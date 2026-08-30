from src.orderflow import market_state


from src.orderflow.features.imbalance import OrderBookImbalance

from src.orderflow.features.microprice import MicroPrice

from src.orderflow.features.ofi import OrderFlowImbalance

from src.orderflow.features.cvd import CVD

from src.orderflow.features.taker_maker_ratio import TakerMakerRatio

from src.orderflow.signal.engine import SignalEngine

from src.orderflow.signal.state_tracker import SignalStateTracker

from src.orderflow.monitor.signal_monitor import SignalMonitor

from src.orderflow.evaluator.signal_evaluator import SignalEvaluator

from src.orderflow.validator.stream_validator import StreamValidator


class OrderFlowEngine:
    """
    数据消费者：从 EventProcessor 接收消息，读全局状态计算指标。

    消息接口（由 EventProcessor 路由调用）：
        on_book_updated   orderbook 数据就绪 → 回读全局 orderbook 算特征
        on_trade_updated  trade 数据就绪     → 回读全局 trade_set 消费新增成交
        on_book_error     orderbook 流出错   → 停掉 book 消费分支
        on_trade_error    trade 流出错       → 停掉 trade 消费分支

    输入:

        全局 orderbook / trade_set（market_state）

    输出:
        {
            timestamp,
            mid,
            microprice,
            spread,
            obi1,
            obi5,
            obi10,
            ofi,
            trade_side,
            trade_price,
            trade_qty,
            cvd,
            buy_breakout,
            sell_breakout
        }
    """

    def __init__(self, recorder=None, signal_recorder=None):

        self.last_timestamp = None

        #
        # trade状态
        #

        self.last_trade = {"side": None, "price": None, "qty": 0}

        #
        # CVD
        #

        self.cvd = CVD()
        # previous CVD value, for computing trade-OFI (CVD diff) per trade
        self.prev_cvd = 0.0

        #
        # Taker-Maker breakout (windowed taker flow vs maker wall)
        #

        self.taker_maker = TakerMakerRatio()

        #
        # OFI
        #

        self.ofi = OrderFlowImbalance()

        #
        # 最近orderbook
        #

        self.order_book = None

        #
        # 当前feature
        #

        self.feature = None

        #
        # 各流是否可用：收到 error 停止消费，收到 updated 自动恢复
        #
        self.book_active = False
        self.trade_active = False

        #
        # 下游业务（原 EventProcessor 的处理管线，随消费职责一起下沉）
        #

        self.recorder = recorder

        self.signal_recorder = signal_recorder

        self.signal_engine = SignalEngine(tofi_threshold=0.0, tofi_scale=1.0)

        self.signal_monitor = SignalMonitor(interval=60)

        self.evaluator = SignalEvaluator()

        self.signal_tracker = SignalStateTracker(emit_flat=True)

        self.validator = StreamValidator(gap_warn_ms=3000, report_every=2000)

    #
    # ======================
    # 消息接口（EventProcessor 路由入口）
    # ======================
    #

    def on_book_updated(self, event):
        """orderbook 数据就绪：回读全局 orderbook，计算特征。

        消费者侧校验：经调度积压后的总滞后超过阈值的消息直接丢掉
        （不算特征、不出信号）。
        """

        self.book_active = True

        if not market_state.book_ready:

            return

        timestamp = event.get("timestamp")

        latency = market_state.now_ms() - timestamp

        if latency > market_state.LATENCY_MAX_MS:

            market_state.log_stale_drop("book", latency)

            return

        feature = self.update_book(market_state.orderbook, timestamp)

        if feature is not None:

            self._handle_feature(feature, "book_updated")

    def on_trade_updated(self, event):
        """trade 数据就绪：回读全局 trade_set，消费全部新增成交。

        无 await，逐笔弹空是原子操作（见 market_state.py）。
        消费者侧校验：滞留超过阈值的成交跳过（弹出但不产生特征）。
        """

        self.trade_active = True

        now_ms = market_state.now_ms()

        while market_state.trade_set:

            trade = market_state.trade_set.popleft()

            latency = now_ms - trade["timestamp"]

            if latency > market_state.LATENCY_MAX_MS:

                market_state.log_stale_drop("trade", latency)

                continue

            feature = self.update_trade(
                trade["price"], trade["qty"], trade["side"], trade["timestamp"]
            )

            if feature is not None:

                self._handle_feature(feature, "trade_updated")

    def on_book_error(self, event):
        """orderbook 流出错：停止 book 消费分支，等下一次 book_updated 恢复。"""

        self.book_active = False

        print(f"[engine] book 流错误，暂停消费: {event.get('error')}")

    def on_trade_error(self, event):
        """trade 流出错：停止 trade 消费分支，等下一次 trade_updated 恢复。"""

        self.trade_active = False

        print(f"[engine] trade 流错误，暂停消费: {event.get('error')}")

    def stop(self):
        """被 EventProcessor.stop() 通知时收尾。"""

        if hasattr(self, "evaluator"):

            self.evaluator.close()

    #
    # ======================
    # 特征计算
    # ======================
    #

    def update_book(self, order_book, timestamp):

        self.order_book = order_book

        self.last_timestamp = timestamp

        #
        # OBI
        #

        obi1 = OrderBookImbalance.calculate(order_book, levels=1)

        obi5 = OrderBookImbalance.calculate(order_book, levels=5)

        obi10 = OrderBookImbalance.calculate(order_book, levels=10)

        #
        # MicroPrice
        #

        micro = MicroPrice.calculate(order_book)

        #
        # mid / spread
        #

        bid = order_book.best_bid()

        ask = order_book.best_ask()

        if bid is None or ask is None:

            return None

        mid = (bid + ask) / 2

        spread = ask - bid

        #
        # OFI
        #

        ofi_value = self.ofi.update(order_book)

        #
        # Taker-Maker breakout: taker flow accumulated over the previous wall's
        # 100ms life, divided by that wall (touch-level depth).
        #

        bid_depth = order_book.bid_volume(bid)
        ask_depth = order_book.ask_volume(ask)
        breakout = self.taker_maker.update_book(timestamp, bid_depth, ask_depth)

        self.feature = {
            "timestamp": timestamp,
            "mid": mid,
            "microprice": micro,
            "spread": spread,
            "obi1": obi1,
            "obi5": obi5,
            "obi10": obi10,
            "ofi": ofi_value,
            "trade_side": self.last_trade["side"],
            "trade_price": self.last_trade["price"],
            "trade_qty": self.last_trade["qty"],
            "cvd": self.cvd.value,
            "bid_depth": bid_depth,
            "ask_depth": ask_depth,
            "buy_breakout": breakout["buy_breakout"],
            "sell_breakout": breakout["sell_breakout"],
            # depth events do not change CVD -> trade-OFI is 0 here
            "tofi": 0.0,
        }

        return dict(self.feature)

    def update_trade(self, price, qty, side, timestamp):

        self.last_timestamp = timestamp

        self.last_trade = {"side": side, "price": price, "qty": qty}

        #
        # 更新CVD
        #

        self.cvd.update(side, qty)

        # trade-OFI = change in CVD since the previous trade
        tofi = self.cvd.value - self.prev_cvd
        self.prev_cvd = self.cvd.value

        #
        # accumulate taker flow for the breakout window
        #

        breakout = self.taker_maker.update_trade(timestamp, side, qty)

        if self.feature is not None:
            f = dict(self.feature)
            f["timestamp"] = timestamp
            f["trade_side"] = side
            f["trade_price"] = price
            f["trade_qty"] = qty
            f["cvd"] = self.cvd.value
            f["tofi"] = tofi
            f["buy_breakout"] = breakout["buy_breakout"]
            f["sell_breakout"] = breakout["sell_breakout"]
            self.feature = f
        else:
            self.feature = {
                "timestamp": timestamp,
                "mid": price,
                "microprice": price,
                "spread": 0.0,
                "obi1": 0.0, "obi5": 0.0, "obi10": 0.0,
                "ofi": 0.0,
                "trade_side": side,
                "trade_price": price,
                "trade_qty": qty,
                "cvd": self.cvd.value,
                "bid_depth": 0.0, "ask_depth": 0.0,
                "buy_breakout": 0.0, "sell_breakout": 0.0,
                "tofi": tofi,
            }

        return dict(self.feature)

    def _handle_feature(self, feature, event_type):

        timestamp = feature["timestamp"]

        #
        # Stream Validator: 校验数据连续性（加工后、落盘前）
        #
        self.validator.check(event_type, feature.get("timestamp"))

        #
        # Signal Evaluator: 持续喂入最新价格
        #
        self.evaluator.update_price(feature["timestamp"], feature["mid"])

        # 捕获当前 mid（用于后续 add_signal 的 entry_mid）
        current_mid = feature["mid"]

        #
        # Feature Recorder
        #
        if self.recorder:

            self.recorder.write(feature)

        #
        # Raw Signal
        #
        signal = self.signal_engine.generate(feature)

        if signal is None:

            return

        #
        # Phase 10.6.3
        #
        # Signal State Filter
        #
        filtered_signal = self.signal_tracker.update(signal)

        #
        # 状态没有变化
        #
        if filtered_signal is None:

            return

        #
        # Signal Monitor
        #
        self.signal_monitor.update(filtered_signal)

        #
        # Signal Evaluator: 记录信号用于收益评估
        #
        self.evaluator.add_signal(filtered_signal, feature, entry_mid=current_mid)

        #
        # Signal Recorder
        #
        if self.signal_recorder:

            self.signal_recorder.write(filtered_signal, feature)

        #
        # 输出变化后的signal（FLAT 不刷屏）
        #
        if filtered_signal.side.value != "FLAT":
            print(
                {
                    "signal": filtered_signal.side.value,
                    "strength": round(filtered_signal.strength, 3),
                    "reason": filtered_signal.reason,
                    "mid": feature.get("mid"),
                    "timestamp": timestamp,
                }
            )

    def snapshot(self):

        return self.feature
