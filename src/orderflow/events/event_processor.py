import traceback


from src.orderflow.events.event_buffer import EventBuffer


from src.orderflow.signal.engine import SignalEngine


from src.orderflow.monitor.signal_monitor import SignalMonitor


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
        self.signal_engine = SignalEngine()


        #
        # Phase 10.6
        # Signal Monitor
        #
        self.signal_monitor = SignalMonitor(
            interval=60
        )


        #
        # Event buffer
        #
        self.buffer = EventBuffer(
            delay_ms=delay_ms
        )


        self.running = True



        #
        # 只打印信号变化
        #
        self.last_signal = None





    async def run(self):

        print(
            "Event processor started"
        )


        while self.running:

            try:

                event = await self.event_queue.get()


                self.buffer.push(
                    event
                )


                ready_events = (
                    self.buffer.pop_ready()
                )


                for item in ready_events:

                    self.process(
                        item
                    )


            except Exception:

                print(
                    "EventProcessor error:"
                )

                traceback.print_exc()







    def process(
        self,
        event
    ):


        event_type = event.get(
            "type"
        )


        timestamp = event.get(
            "timestamp"
        )


        feature = None



        #
        # depth事件
        #
        if event_type == "depth":


            feature = self.engine.update_book(

                event["data"],

                timestamp

            )



        #
        # trade事件
        #
        elif event_type == "trade":


            trade = event["data"]


            feature = self.engine.update_trade(

                trade["price"],

                trade["qty"],

                trade["side"],

                timestamp

            )



        else:

            return





        if feature is None:

            return





        #
        # Feature Recorder
        #
        if self.recorder:


            self.recorder.write(

                feature

            )





        #
        # 生成signal
        #
        signal = self.signal_engine.generate(

            feature

        )



        if signal is None:

            return





        #
        # Phase 10.6
        # Signal统计
        #
        self.signal_monitor.update(

            signal

        )





        #
        # Signal Recorder
        #
        if self.signal_recorder:


            self.signal_recorder.write(

                signal,

                feature

            )







        #
        # 只打印signal变化
        #
        current_signal = signal.side.value



        if current_signal != self.last_signal:


            print(

                {

                    "signal":

                        current_signal,


                    "strength":

                        round(

                            signal.strength,

                            3

                        ),


                    "reason":

                        signal.reason,


                    "mid":

                        feature.get(
                            "mid"
                        ),


                    "timestamp":

                        timestamp

                }

            )


            self.last_signal = current_signal






    def stop(self):

        self.running = False