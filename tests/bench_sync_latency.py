"""对比重构前（串行 _sync）与重构后（双协程分工）的同步耗时。

模拟条件（两条路径完全相同，网络延迟为共同项，公平对比算法结构）：
  - depth@100ms：每 100ms 产出一条连续 depth 事件（每条覆盖 10 个 update id）
  - REST 快照延迟 300ms（连接建立时即开始抓取）
  - 快照 a = REST 完成时刻的流位置（正常情况：不过旧、不超前）

旧路径：复刻重构前的算法 —— 连接后并行缓冲至快照返回，
        然后串行 _sync：每轮收满 30 条事件 → 检查锚点。
新路径：直接运行重构后的 _fill_buffer + _refresh_snapshot 双协程。
"""
import asyncio
import json
import sys

sys.path.insert(0, ".")

import src.orderflow.collector.binance_depth as m
from src.orderflow.book.order_book import OrderBook

EVENT_PACE = 0.1      # depth@100ms
IDS_PER_EVENT = 10    # 每条事件覆盖的 update id 数
REST_LATENCY = 0.3    # REST 快照网络延迟
SYNC_MAX_ATTEMPTS = 40


class FakeStream:
    """按固定节奏产出连续 depth 事件的假 ws"""

    def __init__(self):
        self.last_u = 0

    async def recv(self):
        await asyncio.sleep(EVENT_PACE)
        U = self.last_u + 1
        u = self.last_u + IDS_PER_EVENT
        pu = self.last_u
        self.last_u = u
        return json.dumps({
            "e": "depthUpdate", "U": U, "u": u, "pu": pu,
            "b": [[str(U), "1"]], "a": [[str(u), "1"]], "T": 0, "E": 0,
        })


def make_get_snap(stream):
    async def get_snap():
        await asyncio.sleep(REST_LATENCY)
        return {"lastUpdateId": stream.last_u,
                "bids": [["1", "1"]], "asks": [["2", "1"]]}
    return get_snap


async def old_flow(stream, get_snap):
    """复刻重构前：连接后立即抓快照（并行缓冲），随后串行 _sync。"""
    from sortedcontainers import SortedKeyList

    loop = asyncio.get_running_loop()
    t0 = loop.time()
    buffer = SortedKeyList(key=lambda e: e["U"])

    #
    # 旧 _run_depth 前段：快照任务与缓冲并行
    #
    snap_task = asyncio.create_task(get_snap())
    while not snap_task.done():
        data = json.loads(await stream.recv())
        if data.get("e") == "depthUpdate":
            buffer.add(data)
    snapshot = await snap_task

    #
    # 旧 _sync：每轮收满 30 条 → 刷新快照（过旧则重抓）→ 找锚点
    #
    for attempt in range(1, SYNC_MAX_ATTEMPTS + 1):
        for _ in range(30):
            data = json.loads(await stream.recv())
            if data.get("e") == "depthUpdate":
                buffer.add(data)

        u_min, u_max = (buffer[0]["U"], buffer[-1]["u"]) if buffer else (None, None)
        if u_min is not None and snapshot["lastUpdateId"] < u_min:
            snapshot = await get_snap()

        a = snapshot["lastUpdateId"]
        u_min, u_max = (buffer[0]["U"], buffer[-1]["u"]) if buffer else (None, None)
        if u_max is not None and a > u_max:
            buffer.clear()

        anchor = None
        for e in buffer:
            if e["U"] > a:
                break
            if e["U"] <= a <= e["u"]:
                anchor = e
                break
        if anchor is not None:
            return loop.time() - t0

    raise RuntimeError("old flow exhausted")


async def new_flow(stream, get_snap):
    """直接运行重构后的双协程分工（真实新代码路径）。"""
    from sortedcontainers import SortedKeyList

    loop = asyncio.get_running_loop()
    t0 = loop.time()

    m.get_snapshot = get_snap
    m.save_snapshot = lambda s: None

    shared = m.SharedState()
    buffer = SortedKeyList(key=lambda e: e["U"])
    order_book = OrderBook()
    queue = asyncio.Queue()

    filler = asyncio.create_task(
        m._fill_buffer(stream, buffer, shared, order_book, queue)
    )
    refresher = asyncio.create_task(m._refresh_snapshot(shared))

    while shared.synced_anchor is None:
        await asyncio.sleep(0.005)
        if filler.done():
            raise RuntimeError(f"new flow failed: {filler.exception()}")

    dt = loop.time() - t0
    filler.cancel()
    refresher.cancel()
    await asyncio.gather(filler, refresher, return_exceptions=True)
    return dt


async def main():
    stream_old = FakeStream()
    t_old = await old_flow(stream_old, make_get_snap(stream_old))

    stream_new = FakeStream()
    t_new = await new_flow(stream_new, make_get_snap(stream_new))

    print(f"旧串行 _sync   : {t_old:.2f}s")
    print(f"新双协程分工   : {t_new:.2f}s")
    print(f"同步提速       : {t_old / t_new:.1f}x")


if __name__ == "__main__":
    asyncio.run(main())