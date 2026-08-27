from src.orderflow.features.imbalance import OrderBookImbalance

from src.orderflow.features.microprice import MicroPrice

from src.orderflow.features.ofi import OrderFlowImbalance

from src.orderflow.features.cvd import CVD

from src.orderflow.features.taker_maker_ratio import TakerMakerRatio


class OrderFlowEngine:
    """
    Order Flow Feature Engine


    输入:

        OrderBook event
        Trade event


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

    def __init__(self):

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

        return self.feature

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
            self.feature["timestamp"] = timestamp
            self.feature["trade_side"] = side
            self.feature["trade_price"] = price
            self.feature["trade_qty"] = qty
            self.feature["cvd"] = self.cvd.value
            self.feature["tofi"] = tofi
            self.feature["buy_breakout"] = breakout["buy_breakout"]
            self.feature["sell_breakout"] = breakout["sell_breakout"]

        return self.feature

    def snapshot(self):

        return self.feature
