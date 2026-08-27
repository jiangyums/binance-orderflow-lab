import asyncio
import json
import websockets

URL = "wss://fstream.binance.com/ws"
SYMBOL = "btcusdt"


async def collect_trade():
    async with websockets.connect(
        URL,
        ping_interval=20,
        ping_timeout=60,
    ) as ws:

        await ws.send(
            json.dumps(
                {
                    "method": "SUBSCRIBE",
                    "params": [f"{SYMBOL}@trade"],
                    "id": 1,
                }
            )
        )

        while True:
            message = await ws.recv()
            data = json.loads(message)

            if data.get("e") != "trade":
                continue

            price = float(data["p"])
            quantity = float(data["q"])
            buyer_is_maker = data["m"]

            if buyer_is_maker:
                side = "SELL"
            else:
                side = "BUY"

            print(f"{side:4} " f"price={price:.2f} " f"qty={quantity:.6f}")


if __name__ == "__main__":
    asyncio.run(collect_trade())
