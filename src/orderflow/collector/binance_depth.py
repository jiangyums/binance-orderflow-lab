"""orderbook 数据生产者。

职责：维护全局 orderbook（market_state.orderbook），通过消息通知消费者：
  - 快照+流合并成功后，每收到一条增量 → book_updated
  - 连接断开/流缺口等异常     → book_error（随后自动重连）
本模块不参与任何指标计算。
"""

import asyncio
import json
import os

from sortedcontainers import SortedKeyList

import aiohttp
import websockets


from src.orderflow import market_state

SYMBOL = "btcusdt"


WS_URL = "wss://fstream.binance.com/ws/" f"{SYMBOL}@depth@100ms"


REST_URL = "https://fapi.binance.com" "/fapi/v1/depth"


LIMIT = 1000


SNAPSHOT_DUMP_PATH = "data/snapshot.json"


def validate_snapshot(snapshot):
    """
    启动快照校验，避免使用到损坏/空的快照
    """

    if not isinstance(snapshot, dict):
        raise RuntimeError("snapshot is not a dict")

    if "lastUpdateId" not in snapshot:
        raise RuntimeError("snapshot missing lastUpdateId")

    if not snapshot.get("bids") or not snapshot.get("asks"):
        raise RuntimeError("snapshot bids/asks empty")

    return True


def save_snapshot(snapshot):
    """
    快照落盘，便于审计/排查
    """

    os.makedirs(os.path.dirname(SNAPSHOT_DUMP_PATH), exist_ok=True)

    with open(SNAPSHOT_DUMP_PATH, "w", encoding="utf-8") as f:

        json.dump(snapshot, f)


RECV_TIMEOUT = 30


async def _recv(ws, phase):
    """
    带超时的接收，用于把“静默僵死”变成可观测的异常

    phase 仅用于日志定位（buffer / live）
    """

    try:

        return await asyncio.wait_for(ws.recv(), timeout=RECV_TIMEOUT)

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

    params = {"symbol": SYMBOL.upper(), "limit": LIMIT}

    async with aiohttp.ClientSession() as session:

        async with session.get(url, params=params) as response:

            response.raise_for_status()

            return await response.json()


SYNC_MAX_ATTEMPTS = 40

#
# 等待快照期间缓冲的上限（REST 长时间不可用时兜底，防止内存无限增长）
#
SYNC_BUFFER_CAP = 10000


class SharedState:
    """协程1(_fill_buffer) 与 协程2(_refresh_snapshot) 的共享信号。

    asyncio 单事件循环下，两个协程对本类字段的读写均为
    “不跨 await 的单次赋值/读取”，天然原子，无需加锁（效率）：

      - snapshotflag: True=需要快照。
        _fill_buffer 置位（首次拉取成功/快照过旧）与复位（消费成功），
        _refresh_snapshot 只读。
      - snapshot: 最新 REST 快照。_refresh_snapshot 整体赋值（引用赋值
        原子），_fill_buffer 读取后立即置 None（消费一次即失效，
        防止重复消费）。

    snapshot_event 是 snapshotflag 的 Event 形式：
    协程2 用 Event.wait() 零轮询挂起等待，flag=False 时不消耗 CPU（效率）。
    """

    def __init__(self):

        self.snapshot = None

        self.snapshotflag = False

        self.snapshot_event = asyncio.Event()

        #
        # 同步成功后的观测点（日志/测试用）
        #
        self.synced_snapshot = None

        self.synced_anchor = None

    def request_snapshot(self):
        """_fill_buffer：需要快照 → 置位信号（协程2开始拉取）"""

        self.snapshotflag = True

        self.snapshot_event.set()

    def clear_snapshot_request(self):
        """_fill_buffer：快照消费成功 → 复位信号（协程2停止拉取）"""

        self.snapshotflag = False

        self.snapshot_event.clear()


async def _refresh_snapshot(shared):
    """协程2：snapshotflag 为真时拉取 REST 快照，为假时挂起等待（永不退出）。

    - Event.wait() 零轮询：flag=False 时挂起，不忙等
    - 醒来后先取走“请求”（clear event），拉取期间若有新请求会再次置位，
      不会丢信号
    - 拉取失败：退避后重试（flag 仍为 True 时重新置位 event）
    - 交付前复查 snapshotflag：若期间已被复位（如重连），丢弃本次快照，
      避免把过期快照交给新的同步流程
    """

    while True:

        await shared.snapshot_event.wait()      # flag=False 时挂起，零轮询

        shared.snapshot_event.clear()           # 取走本轮请求

        try:

            snapshot = await get_snapshot()

            validate_snapshot(snapshot)

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            print(
                f"[depth] 快照拉取失败({type(exc).__name__}: {exc})，"
                f"{_RECONNECT_BACKOFF}s 后重试"
            )

            await asyncio.sleep(_RECONNECT_BACKOFF)

            if shared.snapshotflag:

                shared.snapshot_event.set()     # 仍需要 → 保持请求，重试

            continue

        save_snapshot(snapshot)

        if shared.snapshotflag:

            shared.snapshot = snapshot          # 原子赋值，协程1下一轮可见

            print(f"[depth] 快照就绪 lastUpdateId={snapshot['lastUpdateId']}")

        else:

            print("[depth] 快照已不再需要，丢弃")


def _scan_range(buffer):
    """Return (u_min, u_max) over buffered events, or (None, None) if empty."""
    if not buffer:
        return None, None
    return buffer[0]["U"], buffer[-1]["u"]


def _find_anchor(buffer, a):
    """First event whose [U, u] range contains a (Binance doc: U <= a <= u)."""
    for ev in buffer:
        if ev["U"] > a:
            break
        if ev["U"] <= a <= ev["u"]:
            return ev
    return None


def _trim_buffer(buffer, anchor):
    """Drop anchor and everything before it; keep later events for replay."""
    idx = buffer.bisect_left({"U": anchor["U"]})
    while idx < len(buffer) and buffer[idx] is not anchor:
        idx += 1
    del buffer[: idx + 1]


def _try_align(buffer, snapshot):
    """用快照 a=lastUpdateId 对齐缓冲，返回 (anchor, action)。

    action:
      "hit"   — 找到锚点（U <= a <= u），可进入加载/回放
      "stale" — 快照过旧（a < U_min），需重抓快照
      "ahead" — 快照超前（a > u_max），缓冲全过旧，应清空
      "gap"   — a 落在缓冲范围内却无覆盖事件（后续事件 U 只会更大，
                永远无法覆盖）→ 流缺口
    """
    a = snapshot["lastUpdateId"]

    u_min, u_max = _scan_range(buffer)

    if u_max is None:
        return None, "wait"

    if a > u_max:
        return None, "ahead"

    anchor = _find_anchor(buffer, a)

    if anchor is not None:
        return anchor, "hit"

    if u_min is not None and a < u_min:
        return None, "stale"

    return None, "gap"


async def _replay_buffer(buffer, order_book, event_queue):
    """回放缓冲中剩余事件（锚点之后的增量），要求 pu 连续，最后清空缓冲。"""

    for event in list(buffer):

        if event["pu"] != order_book.last_update_id:

            raise OrderBookGapError(
                "OrderBook gap in buffered events: "
                f"pu={event['pu']} "
                f"last={order_book.last_update_id}"
            )

        order_book.apply_update(event)

        #
        # 只发成功更新信号，数据由 processor 回读全局 orderbook
        #
        await event_queue.put(
            {
                "type": "book_updated",
                "timestamp": event.get("T", event["E"]),
            }
        )

    buffer.clear()


async def _fill_buffer(ws, buffer, shared, order_book, event_queue):
    """协程1：唯一的 ws 消费者，持续拉取 depth（永不主动退出）。

    未同步阶段：
      - 第一次成功拉取 → snapshotflag=True，请求快照（协程2开始拉取）
      - shared.snapshot 非空 → 消费（“插入”同步流程）：
          命中锚点 → 加载订单簿、回放剩余缓冲，转入实时阶段
          快照过旧 → 重新置位 snapshotflag 请求重抓
          快照超前 → 清空缓冲，等事件追上快照
    同步完成后：逐条校验 pu 连续性并原地更新全局 orderbook，
    每条增量只向 event_queue 发一个 book_updated 信号（实时阶段）。
    """

    first_ok = False
    current = None             # 当前用于对齐的快照（消费自 shared.snapshot）
    refetch_requested = False  # 当前快照是否已发起过重抓（防止重复请求）
    attempts = 0               # 快照重抓次数（超过上限判定流缺口）
    synced = False
    stale_notified = False     # 滞后过高是否已通知（进入/退出滞后态各通知一次）

    while True:

        message = await _recv(ws, "live" if synced else "buffer")

        data = json.loads(message)

        if data.get("e") != "depthUpdate":
            continue

        if not synced:

            buffer.add(data)

            #
            # 缓冲上限保护：REST 长时间不可用时避免内存无限增长
            #
            if len(buffer) > SYNC_BUFFER_CAP:
                raise OrderBookGapError(
                    f"depth 缓冲超过上限({SYNC_BUFFER_CAP})，疑似快照服务不可用"
                )

            #
            # 第一次拉取成功 → 请求快照
            #
            if not first_ok:
                first_ok = True
                shared.request_snapshot()
                print("[depth] 首次 depth 拉取成功，snapshotflag=True")

            #
            # 消费快照（协程2 → 协程1 的一次性交接）
            #
            if shared.snapshot is not None:
                current = shared.snapshot
                shared.snapshot = None            # 消费后置空，防止重复消费
                shared.clear_snapshot_request()   # snapshotflag=False，协程2停止
                refetch_requested = False
                print(f"[depth] 消费快照 a={current['lastUpdateId']}")

            if current is None:
                continue

            anchor, action = _try_align(buffer, current)

            if action == "ahead":
                #
                # 快照超前：缓冲全过旧，清空等事件追上
                #
                buffer.clear()
                continue

            if action == "hit":
                #
                # 命中锚点：加载快照 → 应用锚点 → 回放剩余缓冲
                #
                _trim_buffer(buffer, anchor)
                order_book.load_snapshot(current)
                order_book.apply_update(anchor)

                #
                # 快照与流已成功合并：置位全局就绪信号，
                # processor 从此开始响应 book_updated
                #
                market_state.book_ready = True

                await event_queue.put(
                    {
                        "type": "book_updated",
                        "timestamp": anchor.get("T", anchor["E"]),
                    }
                )
                await _replay_buffer(buffer, order_book, event_queue)
                shared.synced_snapshot = current
                shared.synced_anchor = anchor
                synced = True
                print(f"[depth] 同步完成 a={current['lastUpdateId']}")
                continue

            if action == "stale" and not refetch_requested:
                #
                # 快照过旧（a < U_min）→ 重新请求快照
                #
                refetch_requested = True
                attempts += 1
                if attempts >= SYNC_MAX_ATTEMPTS:
                    raise OrderBookGapError(
                        "depth 同步超过最大尝试次数，疑似流缺口"
                    )
                u_min, _ = _scan_range(buffer)
                print(
                    f"[depth] 快照过旧(a={current['lastUpdateId']} "
                    f"< U_min={u_min})，重新请求快照"
                )
                shared.request_snapshot()
            continue

        #
        # 实时 depth
        #
        if data["pu"] != order_book.last_update_id:
            raise OrderBookGapError(
                "OrderBook gap detected: "
                f"pu={data['pu']} "
                f"last={order_book.last_update_id}"
            )

        #
        # 生产者侧校验：单条增量不能丢（跳过会破坏 pu 连续性、损坏簿面），
        # 整流滞后过高时改发 book_error 让消费者暂停；
        # 簿面照常维护，延迟恢复后下一个 book_updated 自动让消费者接上
        #
        latency = market_state.now_ms() - data.get("T", data["E"])

        if latency > market_state.LATENCY_MAX_MS:

            if not stale_notified:

                stale_notified = True

                await event_queue.put(
                    {
                        "type": "book_error",
                        "timestamp": market_state.now_ms(),
                        "error": f"depth 滞后 {latency}ms (> "
                                 f"{market_state.LATENCY_MAX_MS}ms)，流整体落后",
                    }
                )

        else:

            stale_notified = False

        order_book.apply_update(data)

        #
        # 只发成功更新信号，数据由 processor 回读全局 orderbook
        #
        await event_queue.put(
            {
                "type": "book_updated",
                "timestamp": data.get("T", data["E"]),
            }
        )


async def _run_depth(order_book, event_queue):

    async with websockets.connect(WS_URL, ping_interval=None) as ws:

        print("Depth websocket connected")

        #
        # 每次连接独立的共享状态：重连后 snapshot/snapshotflag 自动复位
        #
        shared = SharedState()

        buffered_events = SortedKeyList(key=lambda e: e["U"])

        #
        # 协程1（唯一 ws 消费者）+ 协程2（REST 快照）并发；
        # 任一异常（含 OrderBookGapError）→ 退出 → orderbook_worker 重连
        #
        filler = asyncio.create_task(
            _fill_buffer(ws, buffered_events, shared, order_book, event_queue)
        )

        refresher = asyncio.create_task(_refresh_snapshot(shared))

        try:

            await asyncio.gather(filler, refresher)

        finally:

            #
            # 任一协程退出（异常/取消）→ 收掉另一个，避免孤儿任务
            #
            filler.cancel()
            refresher.cancel()
            await asyncio.gather(filler, refresher, return_exceptions=True)


async def orderbook_worker(event_queue):

    #
    # 全局订单簿（market_state.orderbook）：跨重连复用，
    # 本协程是唯一写入方
    #
    order_book = market_state.orderbook

    attempt = 0

    while True:

        try:

            await _run_depth(order_book, event_queue)

            return

        except (
            websockets.exceptions.WebSocketException,
            asyncio.TimeoutError,
            OSError,
            MemoryError,
            OrderBookGapError,
        ) as exc:

            #
            # 通知消费者：book 数据出错（全局簿已不可信，复位就绪标志）
            #
            market_state.book_ready = False

            await event_queue.put(
                {
                    "type": "book_error",
                    "timestamp": market_state.now_ms(),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

            attempt += 1

            print(
                f"[depth] 连接断开/异常（{type(exc).__name__}），"
                f"第 {attempt} 次重连，"
                f"{_RECONNECT_BACKOFF}s 后重试"
            )

            await asyncio.sleep(_RECONNECT_BACKOFF)

            continue

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            market_state.book_ready = False

            await event_queue.put(
                {
                    "type": "book_error",
                    "timestamp": market_state.now_ms(),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

            print(f"[depth] 非重连类异常：{type(exc).__name__}: {exc}")

            raise


async def main():

    queue = asyncio.Queue()

    await orderbook_worker(queue)


if __name__ == "__main__":

    asyncio.run(main())