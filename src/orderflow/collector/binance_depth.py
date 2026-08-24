import asyncio
import json
import os
from collections import deque

import aiohttp
import websockets


from src.orderflow.book.order_book import OrderBook



SYMBOL = "btcusdt"


WS_URL = (
    "wss://fstream.binance.com/ws/"
    f"{SYMBOL}@depth@100ms"
)


REST_URL = (
    "https://fapi.binance.com"
    "/fapi/v1/depth"
)


LIMIT = 1000


SNAPSHOT_DUMP_PATH = "data/snapshot.json"


def validate_snapshot(
    snapshot
):
    """
    启动快照校验，避免使用到损坏/空的快照
    """

    if not isinstance(
        snapshot,
        dict
    ):
        raise RuntimeError(
            "snapshot is not a dict"
        )

    if "lastUpdateId" not in snapshot:
        raise RuntimeError(
            "snapshot missing lastUpdateId"
        )

    if (
        not snapshot.get("bids")
        or not snapshot.get("asks")
    ):
        raise RuntimeError(
            "snapshot bids/asks empty"
        )

    return True


def save_snapshot(
    snapshot
):
    """
    快照落盘，便于审计/排查
    """

    os.makedirs(
        os.path.dirname(
            SNAPSHOT_DUMP_PATH
        ),
        exist_ok=True
    )

    with open(
        SNAPSHOT_DUMP_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            snapshot,
            f
        )



RECV_TIMEOUT = 30


async def _recv(
    ws,
    phase
):
    """
    带超时的接收，用于把“静默僵死”变成可观测的异常

    phase 仅用于日志定位（buffer / sync / live）
    """

    try:

        return await asyncio.wait_for(
            ws.recv(),
            timeout=RECV_TIMEOUT
        )

    except asyncio.TimeoutError:

        print(
            f"[depth] recv 超时({RECV_TIMEOUT}s) @ {phase}，"
            "连接可能已被代理/Binance 掐断"
        )

        raise



_RECONNECT_BACKOFF = 3.0


class OrderBookGapError(Exception):
    """depth 增量不连续，需要重新抓快照并同步"""
    pass


async def get_snapshot():


    url = REST_URL


    params = {
        "symbol": SYMBOL.upper(),
        "limit": LIMIT
    }


    async with aiohttp.ClientSession() as session:


        async with session.get(
            url,
            params=params
        ) as response:


            response.raise_for_status()


            return await response.json()



async def _run_depth(
    order_book,
    event_queue
):

    async with websockets.connect(
        WS_URL,
        ping_interval=None
    ) as ws:

        print(
            "Depth websocket connected"
        )

        #
        # 获取snapshot的同时，单消费者缓存depth事件
        # （避免后台receiver与实时循环同时recv同一连接）
        #
        snapshot_task = asyncio.create_task(
            get_snapshot()
        )

        buffered_events = deque()

        while not snapshot_task.done():

            message = await _recv(
                ws,
                "buffer"
            )

            data = json.loads(
                message
            )

            if data.get("e") != "depthUpdate":
                continue

            buffered_events.append(
                data
            )

        snapshot = (
            snapshot_task.result()
        )

        validate_snapshot(
            snapshot
        )

        save_snapshot(
            snapshot
        )

        print(
            "Snapshot:",
            snapshot["lastUpdateId"]
        )

        order_book.load_snapshot(
            snapshot
        )

        #
        # 找到第一个可衔接的event
        #
        # 规则（Binance Futures）:
        #   - 丢弃 u < lastUpdateId 的陈旧事件
        #   - 第一个命中 U <= lastUpdateId + 1 <= u 的事件为锚点
        #
        # 注意：snapshot返回后，已缓存事件可能全部旧于lastUpdateId，
        # 因此若缓冲中找不到，必须继续从ws读取直到命中。
        #
        synced_event = None

        while synced_event is None:

            while buffered_events:

                event = (
                    buffered_events.popleft()
                )

                if (
                    event["u"]
                    <
                    snapshot["lastUpdateId"]
                ):
                    continue

                if (

                    event["U"]

                    <=
                    snapshot["lastUpdateId"] + 1
                    <=
                    event["u"]

                ):
                    synced_event = event
                    break

            if synced_event is None:

                message = await _recv(
                    ws,
                    "sync"
                )

                data = json.loads(
                    message
                )

                if data.get("e") == "depthUpdate":

                    buffered_events.append(
                        data
                    )

        order_book.apply_update(
            synced_event
        )

        await event_queue.put(
            {
                "type": "depth",
                "timestamp": synced_event["E"],
                "data": order_book.copy(),
            }
        )

        print(
            "Depth synchronized"
        )

        #
        # 回放缓冲中剩余的event，避免丢失快照后的增量
        #
        while buffered_events:

            event = (
                buffered_events.popleft()
            )

            if (
                event["pu"]
                !=
                order_book.last_update_id
            ):
                raise OrderBookGapError(
                    "OrderBook gap in buffered events: "
                    f"pu={event['pu']} "
                    f"last={order_book.last_update_id}"
                )

            order_book.apply_update(
                event
            )

            await event_queue.put(
                {
                    "type": "depth",
                    "timestamp": event["E"],
                    "data": order_book.copy(),
                }
            )

        #
        # 实时depth（单消费者）
        #
        while True:

            message = await _recv(
                ws,
                "live"
            )

            data = json.loads(
                message
            )

            if data.get("e") != "depthUpdate":
                continue

            if (
                data["pu"]
                !=
                order_book.last_update_id
            ):
                raise OrderBookGapError(
                    "OrderBook gap detected: "
                    f"pu={data['pu']} "
                    f"last={order_book.last_update_id}"
                )

            order_book.apply_update(
                data
            )

            await event_queue.put(
                {
                    "type": "depth",
                    "timestamp": data["E"],
                    "data": order_book.copy(),
                }
            )



async def depth_worker(
    event_queue
):

    order_book = OrderBook()

    attempt = 0

    while True:

        try:

            await _run_depth(
                order_book,
                event_queue
            )

            return

        except (
            websockets.exceptions.WebSocketException,
            asyncio.TimeoutError,
            OSError,
            MemoryError,
            OrderBookGapError
        ) as exc:

            attempt += 1

            print(
                f"[depth] 连接断开/异常（{type(exc).__name__}），"
                f"第 {attempt} 次重连，"
                f"{_RECONNECT_BACKOFF}s 后重试"
            )

            await asyncio.sleep(
                _RECONNECT_BACKOFF
            )

            continue

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            print(
                f"[depth] 非重连类异常：{type(exc).__name__}: {exc}"
            )

            raise


async def main():

    queue = asyncio.Queue()

    await depth_worker(
        queue
    )



if __name__ == "__main__":

    asyncio.run(
        main()
    )
