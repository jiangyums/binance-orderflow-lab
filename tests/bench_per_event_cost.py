"""量化实时阶段每条 depth 事件的各环节开销（重点：order_book.copy()）。

模拟真实形态：
  - 订单簿：N 档/侧（BTCUSDT 合约 REST limit=1000 → 满簿约 1000 档/侧）
  - 单条 depthUpdate：b/a 各改 5 档（100ms 窗口的典型更新量）
  - 事件节奏：10 条/秒（每条预算 100ms）

测量项：
  json.loads / apply_update / copy() / 单次全排序 / max(min)
  以及下游 engine.update_book 的整体开销（含 3 次全簿排序）
"""
import json
import sys
import time

sys.path.insert(0, ".")

from src.orderflow.book.order_book import OrderBook
from src.orderflow.engine import OrderFlowEngine

BEST = 100000.0
TICK = 0.1


def build_book(n_levels):
    book = OrderBook()
    book.bids = {round(BEST - i * TICK, 1): 1.0 + (i % 7) * 0.5
                 for i in range(n_levels)}
    book.asks = {round(BEST + TICK + i * TICK, 1): 1.0 + (i % 5) * 0.5
                 for i in range(n_levels)}
    book.last_update_id = 1
    return book


def make_message(n_chg=5):
    b = [[f"{BEST - i * TICK:.1f}", "2.5"] for i in range(n_chg)]
    a = [[f"{BEST + TICK + i * TICK:.1f}", "2.5"] for i in range(n_chg)]
    return json.dumps({
        "e": "depthUpdate", "U": 1, "u": 2, "pu": 0,
        "b": b, "a": a, "T": 0, "E": 0,
    })


def bench(fn, reps=2000):
    t0 = time.perf_counter()
    for _ in range(reps):
        fn()
    return (time.perf_counter() - t0) / reps * 1e6  # µs/op


def main():
    msg = make_message()
    engine = OrderFlowEngine()

    print(f"{'N档/侧':>8} | {'json.loads':>10} | {'apply':>8} | "
          f"{'copy':>8} | {'全排序x1':>9} | {'max':>7} | {'下游engine':>10}")
    print("-" * 78)

    for n in (200, 500, 1000):
        book = build_book(n)

        t_json = bench(lambda: json.loads(msg))
        t_apply = bench(lambda: book.apply_update(json.loads(msg)))
        t_copy = bench(lambda: book.copy())
        t_sort = bench(lambda: sorted(book.bids.items(), reverse=True))
        t_max = bench(lambda: max(book.bids.keys()))
        t_engine = bench(lambda: engine.update_book(book, 0), reps=500)

        print(f"{n:>8} | {t_json:>9.1f}µs | {t_apply:>7.1f}µs | "
              f"{t_copy:>7.1f}µs | {t_sort:>8.1f}µs | {t_max:>6.1f}µs | "
              f"{t_engine:>9.1f}µs")

    #
    # 内存：一次 copy 分配了多少
    #
    book = build_book(1000)
    dict_bytes = sys.getsizeof(book.bids) + sys.getsizeof(book.asks)
    entry_bytes = (1000 * 2) * (sys.getsizeof(1.0) * 2 + 8)  # 粗估：键值对象+槽位
    print(f"\n1000档/侧 copy 一次分配 ≈ "
          f"{(dict_bytes + entry_bytes) / 1024:.0f} KB（2个新dict + ~2000个条目引用）")
    print(f"10条/秒 → 每秒分配 ≈ {(dict_bytes + entry_bytes) * 10 / 1024:.0f} KB")

    #
    # 每秒 CPU 占用估算（10 ev/s）
    #
    n = 1000
    book = build_book(n)
    per_event_collector = (bench(lambda: json.loads(msg))
                           + bench(lambda: book.apply_update(json.loads(msg)))
                           + bench(lambda: book.copy()))
    per_event_downstream = bench(lambda: engine.update_book(book, 0), reps=500)
    total_us = per_event_collector + per_event_downstream
    print(f"\n单事件总开销 ≈ {total_us:.0f}µs（采集端 {per_event_collector:.0f}µs "
          f"+ 下游 {per_event_downstream:.0f}µs）")
    print(f"10条/秒 → CPU ≈ {total_us * 10 / 1000:.1f}ms/s "
          f"（单核占比 ≈ {total_us * 10 / 1e6 * 100:.2f}%）")


if __name__ == "__main__":
    main()