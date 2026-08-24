import asyncio
import json

import websockets



SYMBOL = "btcusdt"


WS_URL = (
    "wss://fstream.binance.com/ws/"
    f"{SYMBOL}@trade"
)



async def _run_trade(
    event_queue
):

    async with websockets.connect(
        WS_URL,
        ping_interval=None
    ) as ws:


        print(
            "Trade websocket connected"
        )


        while True:


            try:

                message = await asyncio.wait_for(
                    ws.recv(),
                    timeout=30
                )

            except asyncio.TimeoutError:

                print(
                    "[trade] recv 超时(30s)，"
                    "连接可能已僵死"
                )

                raise


            trade = json.loads(
                message
            )


            if trade.get("e") != "trade":

                continue



            #
            # Binance字段
            #
            # p: price
            # q: quantity
            # T: trade time
            # m: buyer is maker
            #


            price = float(
                trade["p"]
            )


            qty = float(
                trade["q"]
            )


            timestamp = trade["T"]



            #
            # 主动方向判断
            #
            # m=True:
            #   buyer是maker
            #   => 主动卖
            #
            # m=False:
            #   buyer是taker
            #   => 主动买
            #

            if trade["m"]:

                side = "SELL"

            else:

                side = "BUY"



            #
            # 发送统一事件
            #
            await event_queue.put(
                {

                    "type": "trade",


                    "timestamp":
                        timestamp,


                    "data":
                    {

                        "price":
                            price,


                        "qty":
                            qty,


                        "side":
                            side

                    }

                }
            )



_TRADE_RECONNECT_BACKOFF = 3.0


async def trade_worker(
    event_queue
):

    attempt = 0

    while True:

        try:

            await _run_trade(
                event_queue
            )

            return

        except (
            websockets.exceptions.WebSocketException,
            asyncio.TimeoutError,
            OSError,
            MemoryError
        ) as exc:

            attempt += 1

            print(
                f"[trade] 连接断开/异常（{type(exc).__name__}），"
                f"第 {attempt} 次重连，"
                f"{_TRADE_RECONNECT_BACKOFF}s 后重试"
            )

            await asyncio.sleep(
                _TRADE_RECONNECT_BACKOFF
            )

            continue

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            print(
                f"[trade] 非重连类异常：{type(exc).__name__}: {exc}"
            )

            raise


async def main():


    queue = asyncio.Queue()


    await trade_worker(
        queue
    )



if __name__ == "__main__":


    asyncio.run(
        main()
    )