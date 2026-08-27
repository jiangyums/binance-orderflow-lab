import asyncio
import json

import websockets


from src.orderflow.book.order_book import OrderBook

from src.orderflow.book.binance_snapshot import get_snapshot

from src.orderflow.engine import OrderFlowEngine


from src.orderflow.features.imbalance import OrderBookImbalance


from src.orderflow.features.microprice import MicroPrice

SYMBOL = "btcusdt"


DEPTH_WS = "wss://fstream.binance.com/ws/" f"{SYMBOL}@depth@100ms"


TRADE_WS = "wss://fstream.binance.com/ws/" f"{SYMBOL}@trade"


async def depth_worker(order_book, engine):

    async with websockets.connect(DEPTH_WS) as ws:

        print("Depth connected")

        #
        # 获取 snapshot
        #

        snapshot_task = asyncio.create_task(get_snapshot())

        events = []

        #
        # snapshot期间缓存depth事件
        #

        while not snapshot_task.done():

            msg = await ws.recv()

            data = json.loads(msg)

            if data.get("e") == "depthUpdate":

                events.append(data)

        snapshot = snapshot_task.result()

        print("Snapshot:", snapshot["lastUpdateId"])

        order_book.load_snapshot(snapshot)

        #
        # 找第一个可连接事件
        #

        synced = False

        for event in events:

            if event["u"] < order_book.last_update_id:
                continue

            if event["U"] <= order_book.last_update_id + 1 <= event["u"]:

                order_book.apply_update(event)

                synced = True

                break

        if not synced:

            raise RuntimeError("OrderBook sync failed")

        print("OrderBook synchronized")

        #
        # 实时 depth
        #

        while True:

            msg = await ws.recv()

            data = json.loads(msg)

            if data.get("e") != "depthUpdate":

                continue

            event = data

            #
            # updateId连续性检查
            #

            if event["pu"] != order_book.last_update_id:

                raise RuntimeError(
                    "OrderBook gap detected: "
                    f"pu={event['pu']} "
                    f"last={order_book.last_update_id}"
                )

            #
            # 更新盘口
            #

            order_book.apply_update(event)

            #
            # OrderBook Features
            #

            mid = order_book.mid_price()

            spread = order_book.spread()

            obi1 = OrderBookImbalance.calculate(order_book, levels=1)

            obi5 = OrderBookImbalance.calculate(order_book, levels=5)

            obi10 = OrderBookImbalance.calculate(order_book, levels=10)

            microprice = MicroPrice.calculate(order_book)

            #
            # ⭐ OFI
            #

            ofi = engine.update_ofi(order_book)

            #
            # 更新Engine
            #

            engine.update_book(
                mid, microprice, spread, obi1, obi5, obi10, event["E"], ofi
            )

            snapshot = engine.snapshot()

            if snapshot:

                print(snapshot)


async def trade_worker(engine):

    async with websockets.connect(TRADE_WS) as ws:

        print("Trade connected")

        while True:

            msg = await ws.recv()

            data = json.loads(msg)

            price = float(data["p"])

            qty = float(data["q"])

            if data["m"]:

                side = "SELL"

            else:

                side = "BUY"

            engine.update_trade(price, qty, side, data["E"])


async def main():

    order_book = OrderBook()

    engine = OrderFlowEngine()

    await asyncio.gather(depth_worker(order_book, engine), trade_worker(engine))


if __name__ == "__main__":

    asyncio.run(main())
