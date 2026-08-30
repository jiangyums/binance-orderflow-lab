"""Benchmark: insertion cost across built-in Python containers.

Answers: "which container is fastest for inserting into the middle?"

Run:  python tests/bench_container_insert.py
"""
import random
import sys
import time
from collections import deque


def bench_middle(cls, n):
    """Always insert at the current middle index (container grows to n)."""
    c = cls()
    t0 = time.perf_counter()
    for i in range(n):
        c.insert(len(c) // 2, i)
    return time.perf_counter() - t0


def bench_front(cls, n):
    """Always insert at index 0 (container grows to n)."""
    c = cls()
    t0 = time.perf_counter()
    for i in range(n):
        c.insert(0, i)
    return time.perf_counter() - t0


def bench_fixed_pos(cls, n, pos, reps):
    """Insert at a fixed position inside a large container (size ~n)."""
    c = cls(range(n))
    t0 = time.perf_counter()
    for i in range(reps):
        c.insert(pos, -1)
    return time.perf_counter() - t0


def bench_sorted_insert():
    """Common real-world case: keep the container sorted while inserting."""
    import bisect

    n = 20_000
    lst = []
    t0 = time.perf_counter()
    for i in range(n):
        bisect.insort(lst, i % 997)
    report(f"bisect.insort(list), N={n}", time.perf_counter() - t0, n)

    try:
        from sortedcontainers import SortedList
    except ImportError:
        print("  (sortedcontainers not installed -> skipped)")
        return
    sl = SortedList()
    t0 = time.perf_counter()
    for i in range(n):
        sl.add(i % 997)
    report(f"SortedList.add,      N={n}", time.perf_counter() - t0, n)


def _gen_late_arrivals(rng, n, max_lag=2000):
    """Model A: timeline always advances; 5% of items arrive late (near tail)."""
    stream, v = [], 0
    for _ in range(n):
        v += rng.randint(0, 5)
        if rng.random() < 0.05:
            stream.append(v - rng.randint(1, max_lag))   # late arrival
        else:
            stream.append(v)
    return stream


def _gen_jump_backs(rng, n):
    """Model B: value itself jumps back and continues (deep middle inserts)."""
    stream, v = [], 0
    for _ in range(n):
        if rng.random() < 0.05:
            v = max(0, v - rng.randint(1, 100))
        else:
            v += rng.randint(0, 5)
        stream.append(v)
    return stream


def _bench_mixed(label, stream):
    """Keep order while inserting a mostly-ordered stream: list vs deque vs SortedList."""
    import bisect

    n = len(stream)
    expected = sorted(stream)
    print(f"  -- {label} (N={n}) --")

    lst = []
    t0 = time.perf_counter()
    for x in stream:
        bisect.insort(lst, x)
    report("bisect.insort(list)", time.perf_counter() - t0, n)
    assert lst == expected

    # deque has no search; best idiom = O(1) end ops (pop/append from tail)
    dq = deque()
    t0 = time.perf_counter()
    for x in stream:
        if not dq or dq[-1] <= x:        # in-order fast path: O(1)
            dq.append(x)
        else:                            # out-of-order: pop tail, re-push
            tmp = []
            while dq and dq[-1] > x:
                tmp.append(dq.pop())
            dq.append(x)
            dq.extend(reversed(tmp))
    report("deque tail-pop idiom", time.perf_counter() - t0, n)
    assert list(dq) == expected

    try:
        from sortedcontainers import SortedList
    except ImportError:
        print("  (sortedcontainers not installed -> skipped)")
        return
    sl = SortedList()
    t0 = time.perf_counter()
    for x in stream:
        sl.add(x)
    report("SortedList.add", time.perf_counter() - t0, n)
    assert list(sl) == expected


def report(label, seconds, ops):
    print(f"  {label:<26} {seconds * 1000:10.1f} ms total"
          f"   {seconds / ops * 1e6:8.2f} us/op")


def main():
    print(f"Python {sys.version.split()[0]}")
    print()

    print("[1] insert at current MIDDLE, growing to N")
    n = 20_000
    report(f"list.insert(N//2),  N={n}", bench_middle(list, n), n)
    report(f"deque.insert(N//2), N={n}", bench_middle(deque, n), n)
    print()

    print("[2] insert at index 0 (HEAD), growing to N")
    n = 10_000
    report(f"list.insert(0),     N={n}", bench_front(list, n), n)
    report(f"deque.insert(0),    N={n}", bench_front(deque, n), n)
    print()

    print("[3] insert at fixed pos=1000 inside container of N=100_000 (500 reps)")
    n, pos, reps = 100_000, 1000, 500
    report("list.insert(1000)", bench_fixed_pos(list, n, pos, reps), reps)
    report("deque.insert(1000)", bench_fixed_pos(deque, n, pos, reps), reps)
    print()

    print("[4] sorted insertion (keep order while inserting), growing to N")
    bench_sorted_insert()
    print()

    print("[6] PURE in-order tail insertion (best case for every container)")
    n = 200_000
    for name, cls, add in (
        ("list.append", list, lambda c, x: c.append(x)),
        ("deque.append", deque, lambda c, x: c.append(x)),
        ("SortedList.add", None, None),   # filled below if installed
    ):
        if cls is None:
            try:
                from sortedcontainers import SortedList
            except ImportError:
                print("  (sortedcontainers not installed -> skipped)")
                continue
            c, add = SortedList(), lambda c, x: c.add(x)
        else:
            c = cls()
        t0 = time.perf_counter()
        for i in range(n):
            add(c, i)
        report(f"{name}, N={n}", time.perf_counter() - t0, n)
    print()

    print("[5a] mixed stream: 95% in-order + 5% late arrivals (near-tail)")
    _bench_mixed("late arrivals, lag <= 2000 units",
                 _gen_late_arrivals(random.Random(42), 50_000))
    print()

    print("[5b] mixed stream: 95% in-order + 5% value jump-backs (deep middle)")
    _bench_mixed("value jump-backs",
                 _gen_jump_backs(random.Random(42), 50_000))


if __name__ == "__main__":
    main()