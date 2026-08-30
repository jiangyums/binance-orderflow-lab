"""trade 数据生产者。

职责：把每笔成交追加到全局 trade_set（market_state.trade_set），
通过消息通知消费者：
  - 每收到一笔成交 → trade_updated
  - 连接断开等异常   → trade_error（随后自动重连）
本模块不参与任何指标计算。
"""

import asyncio
import json

import websockets

from src.orderflow import market_state

SYMBOL = "btcusdt"


WS_URL = "wss://fstream.binance.com/ws/" f"{SYMBOL}@trade"


async def _run_trade(event_queue):

    async with websockets.connect(WS_URL, ping_interval=None) as ws:

        print("Trade websocket connected")

        while True:

            try:

                message = await asyncio.wait_for(ws.recv(), timeout=30)

            except asyncio.TimeoutError:

                print("[trade] recv 超时(30s)，" "连接可能已僵死")

                raise

            trade = json.loads(message)

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

            price = float(trade["p"])

            qty = float(trade["q"])

            timestamp = trade["T"]

            #
            # 生产者侧校验：滞后过高的成交直接丢弃（不入 trade_set）。
            # 成交之间相互独立，单笔丢弃不破坏任何状态。
            #
            latency = market_state.now_ms() - timestamp

            if latency > market_state.LATENCY_MAX_MS:

                market_state.log_stale_drop("trade", latency)

                continue

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
            # 追加进全局成交集合，再发成功更新信号
            # （数据由 processor 回读全局 trade_set）
            #
            market_state.trade_set.append(
                {"timestamp": timestamp, "price": price, "qty": qty, "side": side}
            )

            await event_queue.put(
                {
                    "type": "trade_updated",
                    "timestamp": timestamp,
                }
            )


_TRADE_RECONNECT_BACKOFF = 3.0


async def trade_worker(event_queue):

    attempt = 0

    while True:

        try:

            await _run_trade(event_queue)

            return

        except (
            websockets.exceptions.WebSocketException,
            asyncio.TimeoutError,
            OSError,
            MemoryError,
        ) as exc:

            #
            # 通知消费者：trade 数据出错
            #
            await event_queue.put(
                {
                    "type": "trade_error",
                    "timestamp": market_state.now_ms(),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

            attempt += 1

            print(
                f"[trade] 连接断开/异常（{type(exc).__name__}），"
                f"第 {attempt} 次重连，"
                f"{_TRADE_RECONNECT_BACKOFF}s 后重试"
            )

            await asyncio.sleep(_TRADE_RECONNECT_BACKOFF)

            continue

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            await event_queue.put(
                {
                    "type": "trade_error",
                    "timestamp": market_state.now_ms(),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

            print(f"[trade] 非重连类异常：{type(exc).__name__}: {exc}")

            raise


async def main():

    queue = asyncio.Queue()

    await trade_worker(queue)


if __name__ == "__main__":

    asyncio.run(main())
