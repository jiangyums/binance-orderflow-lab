import asyncio

import traceback

from asyncio import Queue


from src.orderflow.collector.binance_depth import (
    depth_worker
)

from src.orderflow.collector.binance_trade import (
    trade_worker
)


from src.orderflow.events.event_processor import (
    EventProcessor
)


from src.orderflow.engine import (
    OrderFlowEngine
)


from src.orderflow.recorder.feature_recorder import (
    FeatureRecorder
)


from src.orderflow.recorder.signal_recorder import (
    SignalRecorder
)



async def main():


    print(
        "Starting Binance OrderFlow Lab"
    )


    #
    # Event Queue
    #
    event_queue = Queue()



    #
    # OrderFlow Engine
    #
    engine = OrderFlowEngine()



    #
    # Feature CSV
    #
    feature_recorder = FeatureRecorder(
        "data/features.csv"
    )



    #
    # Signal CSV
    #
    signal_recorder = SignalRecorder(
        "data/signals.csv"
    )



    #
    # Event Processor
    #
    processor = EventProcessor(

        event_queue,

        engine,

        feature_recorder,

        signal_recorder

    )



    #
    # Binance Depth
    #
    depth_task = asyncio.create_task(

        depth_worker(
            event_queue
        )

    )



    #
    # Binance Trade
    #
    trade_task = asyncio.create_task(

        trade_worker(
            event_queue
        )

    )



    #
    # Processor
    #
    processor_task = asyncio.create_task(

        processor.run()

    )



    try:


        await asyncio.gather(

            depth_task,

            trade_task,

            processor_task

        )


    except KeyboardInterrupt:


        print(
            "Stopping..."
        )


    except Exception as exc:


        print(
            "\n[main] 检测到 worker 异常，堆栈如下："
        )

        print(
            f"  异常类型: {type(exc).__name__}"
        )

        print(
            f"  异常信息: {exc}"
        )

        traceback.print_exception(
            type(exc),
            exc,
            exc.__traceback__
        )


    finally:


        processor.stop()


        feature_recorder.close()


        signal_recorder.close()



if __name__ == "__main__":


    asyncio.run(
        main()
    )