import asyncio


async def process_events(event_queue, order_book, engine):

    while True:

        event = await event_queue.get()

        if event is None:

            await asyncio.sleep(0.001)

            continue

        if event["type"] == "trade":

            data = event["data"]

            side = "SELL" if data["m"] else "BUY"

            engine.update_trade(
                float(data["p"]), float(data["q"]), side, event["timestamp"]
            )

        elif event["type"] == "depth":

            order_book.apply_update(event["data"])

            # 重新计算feature

            ofi = engine.update_ofi(order_book)

            ...
