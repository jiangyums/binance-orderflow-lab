import asyncio
import json
import sys

from sortedcontainers import SortedKeyList

sys.path.insert(0, ".")

import src.orderflow.collector.binance_depth as m
from src.orderflow.book.order_book import OrderBook


def ev(U, u, t=0):
    """构造一条 depth 事件（含 b/a，供 OrderBook.apply_update 使用）"""
    return json.dumps({
        "e": "depthUpdate", "U": U, "u": u, "pu": U - 1,
        "b": [[str(U), "1"]], "a": [[str(u), "1"]],
        "T": t, "E": t,
    })


def snap(last_id):
    return {"lastUpdateId": last_id, "bids": [["1", "1"]], "asks": [["2", "1"]]}


async def run(fetches, snapshots):
    """跑一遍双协程流程（_fill_buffer + _refresh_snapshot），返回观测结果。

    fetches:   fake _recv 按序返回的 JSON 串；耗尽后生成“延续事件”
               （u 从上次结束处 +1 继续），保证 live 阶段 pu 不断裂
    snapshots: fake get_snapshot 按序返回；耗尽后重复最后一个
    """
    fetch_iter = iter(fetches)
    snap_iter = iter(snapshots)
    fetched = []
    state = {"last_u": 0}

    async def fake_recv(ws, phase):
        await asyncio.sleep(0)  # 模拟真实 recv 的让出，给协程2调度机会
        try:
            msg = next(fetch_iter)
        except StopIteration:
            u = state["last_u"]
            msg = ev(u + 1, u + 10)  # 延续事件，保证 live 阶段 pu 连续
        state["last_u"] = json.loads(msg)["u"]
        return msg

    async def fake_get_snap():
        s = next(snap_iter, None)
        if s is None:
            s = snapshots[-1]
        fetched.append(s)
        return s

    m._recv = fake_recv
    m.get_snapshot = fake_get_snap
    m.save_snapshot = lambda s: None  # 测试不落盘

    shared = m.SharedState()
    buffer = SortedKeyList(key=lambda e: e["U"])
    order_book = OrderBook()
    queue = asyncio.Queue()

    filler = asyncio.create_task(
        m._fill_buffer(object(), buffer, shared, order_book, queue)
    )
    refresher = asyncio.create_task(m._refresh_snapshot(shared))

    #
    # 最多等 5s：要么同步完成（再跑几轮 live），要么 filler 抛异常
    #
    for _ in range(1000):
        if filler.done():
            break
        if shared.synced_anchor is not None:
            for _ in range(50):
                await asyncio.sleep(0.001)  # 让 live 阶段再处理几条
                if filler.done():
                    break
            break
        await asyncio.sleep(0.005)

    exc = None
    if filler.done() and not filler.cancelled():
        exc = filler.exception()

    filler.cancel()
    refresher.cancel()
    await asyncio.gather(filler, refresher, return_exceptions=True)

    return {
        "synced_anchor": shared.synced_anchor,
        "synced_snapshot": shared.synced_snapshot,
        "snapshot": shared.snapshot,
        "snapshotflag": shared.snapshotflag,
        "book": order_book,
        "queue": queue,
        "buffer": buffer,
        "exc": exc,
        "fetched": fetched,
    }


def check(name, got, expect):
    status = "PASS" if got == expect else "FAIL"
    print(f"[{status}] {name}: got={got} expect={expect}")
    return got == expect


async def main():
    all_pass = True

    # A. 正常：锚点立即命中（事件与快照重叠，U<=lastUpdateId<=u）
    # 快照 a=100；事件 [95,105] 覆盖 100 → 锚点；[106,115] 留在缓冲回放
    r = await run(fetches=[ev(95, 105), ev(106, 115)], snapshots=[snap(100)])
    all_pass &= check("A synced", r["synced_anchor"] is not None, True)
    all_pass &= check("A anchor U",
                      r["synced_anchor"]["U"] if r["synced_anchor"] else None, 95)
    all_pass &= check("A snapshot consumed (None)", r["snapshot"], None)
    all_pass &= check("A flag reset", r["snapshotflag"], False)
    all_pass &= check("A buffer drained", len(r["buffer"]) == 0, True)
    all_pass &= check("A book progressed",
                      (r["book"].last_update_id or 0) >= 115, True)
    all_pass &= check("A queue has events", r["queue"].qsize() >= 3, True)

    # B. 快照太旧：首次 a=100 < U_min=500 → 重新请求 → 第二次 a=505 命中
    r = await run(fetches=[ev(500, 510), ev(511, 520), ev(521, 530), ev(531, 540)],
                  snapshots=[snap(100), snap(505)])
    all_pass &= check("B refetched snapshot",
                      r["synced_snapshot"]["lastUpdateId"] if r["synced_snapshot"] else None, 505)
    all_pass &= check("B anchor U",
                      r["synced_anchor"]["U"] if r["synced_anchor"] else None, 500)
    all_pass &= check("B fetched twice", len(r["fetched"]) >= 2, True)

    # C. 快照太新：a=200 超过缓冲 → 清空缓冲，等事件追上
    r = await run(fetches=[ev(111, 120), ev(121, 130), ev(191, 200),
                           ev(201, 210), ev(211, 220)],
                  snapshots=[snap(200)])
    all_pass &= check("C anchor U",
                      r["synced_anchor"]["U"] if r["synced_anchor"] else None, 191)

    # D. 永远错位：快照永远过旧 → 重抓 40 次后抛 OrderBookGapError（不死循环）
    r = await run(fetches=[ev(500, 510)] * 200, snapshots=[snap(100)] * 50)
    all_pass &= check("D exhaustion raises",
                      isinstance(r["exc"], m.OrderBookGapError), True)

    print("\nALL PASS" if all_pass else "\nSOME FAILED")
    return all_pass


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)