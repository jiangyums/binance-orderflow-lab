import asyncio

import traceback

import argparse

from asyncio import Queue


from src.orderflow import market_state

from src.orderflow.collector.binance_depth import orderbook_worker

from src.orderflow.collector.binance_trade import trade_worker


from src.orderflow.events.event_processor import EventProcessor


from src.orderflow.engine import OrderFlowEngine


from src.orderflow.recorder.feature_recorder import FeatureRecorder


from src.orderflow.recorder.signal_recorder import SignalRecorder


async def main(features_file="data/features.csv", signals_file="data/signals.csv"):

    print("Starting Binance OrderFlow Lab")

    #
    # 服务器时间校准：所有延迟计算统一走服务器时间轴。
    # 失败不阻塞启动（退化为本机时钟），worker 的重连机制自行兜底
    #
    await market_state.calibrate_clock()

    #
    # Event Queue
    #
    event_queue = Queue()

    #
    # OrderFlow Engine（数据消费者，持有全部业务管线）
    #
    feature_recorder = FeatureRecorder(features_file)

    signal_recorder = SignalRecorder(signals_file)

    engine = OrderFlowEngine(recorder=feature_recorder, signal_recorder=signal_recorder)

    #
    # Event Processor（纯调度者：收消息 → 重排 → 路由给 engine）
    #
    processor = EventProcessor(event_queue, engine)

    #
    # Binance Depth（数据生产者）
    #
    depth_task = asyncio.create_task(orderbook_worker(event_queue))

    #
    # Binance Trade（数据生产者）
    #
    trade_task = asyncio.create_task(trade_worker(event_queue))

    #
    # Processor
    #
    processor_task = asyncio.create_task(processor.run())

    try:

        await asyncio.gather(depth_task, trade_task, processor_task)

    except KeyboardInterrupt:

        print("Stopping...")

    except Exception as exc:

        print("\n[main] 检测到 worker 异常，堆栈如下：")

        print(f"  异常类型: {type(exc).__name__}")

        print(f"  异常信息: {exc}")

        traceback.print_exception(type(exc), exc, exc.__traceback__)

    finally:

        processor.stop()

        feature_recorder.close()

        signal_recorder.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Binance OrderFlow Lab recorder")
    parser.add_argument("--features", default="data/features.csv")
    parser.add_argument("--signals", default="data/signals.csv")
    args = parser.parse_args()

    asyncio.run(main(args.features, args.signals))
