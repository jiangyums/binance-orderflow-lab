import asyncio
import json
import websockets

URL = "wss://fstream.binance.com/ws"


async def main():
    print("Connecting:", URL)

    async with websockets.connect(
        URL,
        ping_interval=20,
        ping_timeout=60,
    ) as ws:

        print("Connected")

        request = {
            "method": "SUBSCRIBE",
            "params": [
                "btcusdt@trade",
            ],
            "id": 1,
        }

        await ws.send(json.dumps(request))

        while True:
            message = await ws.recv()
            data = json.loads(message)

            print(data)


if __name__ == "__main__":
    asyncio.run(main())
