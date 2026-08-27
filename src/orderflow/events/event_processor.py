import traceback


from src.orderflow.events.event_buffer import EventBuffer


from src.orderflow.signal.engine import SignalEngine


from src.orderflow.signal.state_tracker import SignalStateTracker


from src.orderflow.monitor.signal_monitor import SignalMonitor
from src.orderflow.evaluator.signal_evaluator import SignalEvaluator


class EventProcessor:

    def __init__(
        self,
        event_queue,
        engine,
        recorder=None,
        signal_recorder=None,
        delay_ms=100,
    ):

        self.event_queue = event_queue

        self.engine = engine

        self.recorder = recorder

        self.signal_recorder = signal_recorder

        #
        # Signal Engine
        #
        self.signal_engine = SignalEngine(tofi_threshold=0.0, tofi_scale=1.0)

        #
        # Phase 10.6
        # Signal Monitor
        #
        self.signal_monitor = SignalMonitor(interval=60)

        self.evaluator = SignalEvaluator()

        #
        # Phase 10.6.3
        # Signal State Filter
        #
        self.signal_tracker = SignalStateTracker(emit_flat=True)

        #
        # Event buffer
        #
        self.buffer = EventBuffer(delay_ms=delay_ms)

        self.running = True

    async def run(self):

        print("Event processor started")

        while self.running:

            try:

                event = await self.event_queue.get()

                self.buffer.push(event)

                ready_events = self.buffer.pop_ready()

                for item in ready_events:

                    self.process(item)

            except Exception:

                print("EventProcessor error:")

                traceback.print_exc()

    def process(self, event):

        event_type = event.get("type")

        timestamp = event.get("timestamp")

        feature = None

        #
        # depth事件
        #
        if event_type == "depth":

            feature = self.engine.update_book(event["data"], timestamp)

        #
        # trade事件
        #
        elif event_type == "trade":

            trade = event["data"]

            feature = self.engine.update_trade(
                trade["price"], trade["qty"], trade["side"], timestamp
            )

        else:

            return

        if feature is None:

            return

        #
        # Signal Evaluator: 持续喂入最新价格
        self.evaluator.update_price(feature["timestamp"], feature["mid"])

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
        self.evaluator.add_signal(filtered_signal, feature)

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

    def stop(self):

        self.running = False

        if hasattr(self, "evaluator"):

            self.evaluator.close()
