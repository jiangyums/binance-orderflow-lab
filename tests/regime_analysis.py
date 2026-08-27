import argparse
import bisect
import csv
import os

from src.orderflow.signal.engine import SignalEngine
from src.orderflow.signal.signal import SignalSide
from src.orderflow.signal.state_tracker import SignalStateTracker


DEFAULT_FEE = 0.0004  # per-side fee (~0.04% taker)
WINDOW_MS = 60000     # trailing volatility window


def _half_spread(spread, mid):
    try:
        s = float(spread)
        m = float(mid)
    except (ValueError, TypeError):
        return 0.0
    if s <= 0 or m <= 0:
        return 0.0
    return s / (2.0 * m)


def _pct(sorted_vals, q):
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, int(q * (len(sorted_vals) - 1)))
    return sorted_vals[idx]


def load_rows(features_path):
    rows = []
    with open(features_path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            feat = {}
            for k, v in row.items():
                if k == "timestamp":
                    feat[k] = int(v)
                else:
                    try:
                        feat[k] = float(v)
                    except (ValueError, TypeError):
                        feat[k] = v
            rows.append(feat)
    return rows


def trailing_vol(timestamps, mids, window_ms):
    """Rolling std of mid returns over a trailing time window, per row."""
    n = len(mids)
    r = [0.0] * n
    for i in range(1, n):
        if mids[i - 1]:
            r[i] = (mids[i] - mids[i - 1]) / mids[i - 1]

    S = [0.0] * (n + 1)
    S2 = [0.0] * (n + 1)
    for i in range(n):
        S[i + 1] = S[i] + r[i]
        S2[i + 1] = S2[i] + r[i] * r[i]

    vol = [0.0] * n
    for i in range(n):
        j = bisect.bisect_left(timestamps, timestamps[i] - window_ms)
        count = i - j + 1
        if count < 5:
            continue
        s = S[i + 1] - S[j]
        s2 = S2[i + 1] - S2[j]
        mean = s / count
        var = max(s2 / count - mean * mean, 0.0)
        vol[i] = var ** 0.5
    return vol


def part1_move_distribution(timestamps, mids, fee):
    """Unconditional short-horizon move magnitude vs cost."""
    taker_cost = 2.0 * fee
    maker_cost = 0.0002
    print("\n=== PART 1: 短周期移动幅度分布 (所有行) ===")
    print("(看 |move| 超过成本的频率 = 出现'足够大 dislocation'的机会)\n")
    print(
        "%-6s %-9s %-9s %-9s %-9s %-10s %-10s"
        % ("hor", "median", "p90", "p95", "p99",
           "%>=taker", "%>=maker")
    )
    for horizon in (1000, 5000, 10000):
        moves = []
        for i in range(len(timestamps)):
            idx = bisect.bisect_left(timestamps, timestamps[i] + horizon)
            if idx < len(timestamps) and mids[i]:
                moves.append(abs((mids[idx] - mids[i]) / mids[i]))
        moves.sort()
        if not moves:
            continue
        p90 = _pct(moves, 0.90)
        p95 = _pct(moves, 0.95)
        p99 = _pct(moves, 0.99)
        ge_taker = sum(1 for m in moves if m >= taker_cost) / len(moves)
        ge_maker = sum(1 for m in moves if m >= maker_cost) / len(moves)
        print(
            "%-6d %-9.5f %-9.5f %-9.5f %-9.5f %-9.2f%% %-9.2f%%"
            % (
                horizon // 1000,
                moves[len(moves) // 2], p90, p95, p99,
                ge_taker * 100, ge_maker * 100,
            )
        )
    print(
        "\ntaker 成本=2xfee=%.4f, maker 成本(参考)=0.0002" % taker_cost
    )


def quantile_thresholds(vals, k):
    s = sorted(v for v in vals if v is not None)
    if not s or k <= 1:
        return []
    return [_pct(s, (i + 1) / k) for i in range(k - 1)]


def bucket_index(value, thresholds):
    idx = 0
    for t in thresholds:
        if value > t:
            idx += 1
        else:
            break
    return idx


def add_signal(B, b, side, entry, spread, t0, g1, g5, g10, fee,
               timestamps, mids, spreads):
    d = B.setdefault(b, {"n": 0, "win": [], "n1": [], "n5": [], "n10": []})
    half_entry = _half_spread(spread, entry)
    for horizon, gross, key in (
        (1000, g1, "n1"),
        (5000, g5, "n5"),
        (10000, g10, "n10"),
    ):
        idx = bisect.bisect_left(timestamps, t0 + horizon)
        if idx >= len(timestamps):
            return
        cost = half_entry + _half_spread(spreads[idx], mids[idx]) + 2.0 * fee
        pnl = gross if side == "LONG" else -gross
        d[key].append(pnl - cost)
        if key == "n10":
            win = (side == "LONG" and gross > 0) or (
                side == "SHORT" and gross < 0
            )
            d["win"].append(1 if win else 0)
            d["n"] += 1


def part2_regime(threshold, fee, rows, timestamps, mids, spreads, ofi_arr, vol, k, obi_weight=0.6, ofi_weight=0.4, ofi_scale=10.0, ofi_mode="linear", ofi_rank_fn=None, ofi_top_pct=0.0):
    eng = SignalEngine(threshold=threshold, obi_weight=obi_weight, ofi_weight=ofi_weight, ofi_scale=ofi_scale, ofi_mode=ofi_mode, ofi_rank_fn=ofi_rank_fn)
    tracker = SignalStateTracker(emit_flat=True)

    # collect emitted signals with their row index + reg/ofi context
    sigs = []
    for i, feat in enumerate(rows):
        sig = eng.generate(feat)
        if sig is None:
            continue
        filtered = tracker.update(sig)
        if filtered is None:
            continue
        if filtered.side == SignalSide.FLAT:
            continue
        sigs.append(
            {
                "i": i,
                "side": filtered.side.value,
                "entry": feat["mid"],
                "spread": feat.get("spread", 0.0),
                "reg": vol[i],
                "ofi": abs(ofi_arr[i]) if i < len(ofi_arr) else 0.0,
            }
        )

    if ofi_top_pct > 0 and sigs:
        em = sorted(s["ofi"] for s in sigs)
        cutoff = em[int((100.0 - ofi_top_pct) / 100.0 * (len(em) - 1))]
        sigs = [s for s in sigs if s["ofi"] >= cutoff]

    reg_thr = quantile_thresholds([s["reg"] for s in sigs], k)
    ofi_thr = quantile_thresholds([s["ofi"] for s in sigs], k)
    reg_b = {}
    ofi_b = {}

    for s in sigs:
        i = s["i"]
        t0 = timestamps[i]
        entry = s["entry"]
        i1 = bisect.bisect_left(timestamps, t0 + 1000)
        i5 = bisect.bisect_left(timestamps, t0 + 5000)
        i10 = bisect.bisect_left(timestamps, t0 + 10000)
        if i1 >= len(timestamps) or i5 >= len(timestamps) or i10 >= len(timestamps):
            continue
        g1 = (mids[i1] - entry) / entry
        g5 = (mids[i5] - entry) / entry
        g10 = (mids[i10] - entry) / entry
        rb = bucket_index(s["reg"], reg_thr)
        ob = bucket_index(s["ofi"], ofi_thr)
        add_signal(reg_b, rb, s["side"], entry, s["spread"], t0,
                   g1, g5, g10, fee, timestamps, mids, spreads)
        add_signal(ofi_b, ob, s["side"], entry, s["spread"], t0,
                   g1, g5, g10, fee, timestamps, mids, spreads)

    return reg_b, ofi_b


def main():
    ap = argparse.ArgumentParser(
        description="Regime analysis: test if the edge is volatility/impulse-dependent."
    )
    ap.add_argument("--features", default="data/features.csv")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--fee", type=float, default=DEFAULT_FEE)
    ap.add_argument("--buckets", type=int, default=10,
                    help="equal-count buckets (deciles=10)")
    ap.add_argument("--obi-weight", type=float, default=0.6,
                    help="OBI weight in SignalEngine (default 0.6)")
    ap.add_argument("--ofi-weight", type=float, default=0.4,
                    help="OFI weight in SignalEngine (default 0.4)")
    ap.add_argument("--ofi-scale", type=float, default=10.0,
                    help="OFI strength divisor (linear mode): strength=min(|ofi|/scale,1)")
    ap.add_argument("--ofi-mode", default="linear",
                    choices=["linear", "rank"],
                    help="OFI strength mode: linear (scalar) or rank (percentile of |ofi|)")
    ap.add_argument("--ofi-top-pct", type=float, default=0.0,
                    help="if >0, only trade signals whose |ofi| is in the top P%% of the session")
    args = ap.parse_args()

    if not os.path.exists(args.features):
        print("features file not found: %s" % args.features)
        return

    k = max(2, args.buckets)
    rows = load_rows(args.features)
    timestamps = [r["timestamp"] for r in rows]
    mids = [r["mid"] for r in rows]
    spreads = [r.get("spread", 0.0) for r in rows]
    ofi_arr = [r.get("ofi", 0.0) for r in rows]
    vol = trailing_vol(timestamps, mids, WINDOW_MS)

    part1_move_distribution(timestamps, mids, args.fee)

    ofi_rank_fn = None
    if args.ofi_mode == "rank":
        _vals = sorted(abs(float(v)) for v in ofi_arr)
        _n = len(_vals)
        ofi_rank_fn = (
            (lambda x: bisect.bisect_right(_vals, x) / _n) if _n else (lambda x: 0.0)
        )

    reg_b, ofi_b = part2_regime(
        args.threshold, args.fee, rows, timestamps, mids, spreads, ofi_arr, vol, k,
        args.obi_weight, args.ofi_weight, args.ofi_scale, args.ofi_mode, ofi_rank_fn,
        args.ofi_top_pct,
    )

    def show(title, buckets):
        print("\n=== %s (threshold=%.1f, %d buckets) ==="
              % (title, args.threshold, k))
        print("%-5s %-8s %-8s %-9s %-9s %-9s"
              % ("bucket", "n", "win10%", "net1", "net5", "net10"))
        A = {"win": [], "n1": [], "n5": [], "n10": [], "n": 0}
        for b in range(k):
            d = buckets.get(b)
            if not d or d["n"] == 0:
                print("%-5d %-8s %-8s %-9s %-9s %-9s"
                      % (b + 1, 0, "-", "-", "-", "-"))
                continue
            n = d["n"]
            win = sum(d["win"]) / n * 100
            n1 = sum(d["n1"]) / n
            n5 = sum(d["n5"]) / n
            n10 = sum(d["n10"]) / n
            print("%-5d %-8d %-7.1f%% %-9.5f %-9.5f %-9.5f"
                  % (b + 1, n, win, n1, n5, n10))
            A["win"].extend(d["win"])
            A["n1"].extend(d["n1"])
            A["n5"].extend(d["n5"])
            A["n10"].extend(d["n10"])
            A["n"] += n
        aw = sum(A["win"]) / A["n"] * 100 if A["n"] else 0.0
        a1 = sum(A["n1"]) / A["n"] if A["n"] else 0.0
        a5 = sum(A["n5"]) / A["n"] if A["n"] else 0.0
        a10 = sum(A["n10"]) / A["n"] if A["n"] else 0.0
        print("%-5s %-8d %-7.1f%% %-9.5f %-9.5f %-9.5f"
              % ("ALL", A["n"], aw, a1, a5, a10))

    show("PART 2a: 按波动regime分段 (trailing 60s vol)", reg_b)
    show("PART 2b: 按订单流冲击 |OFI| 分段", ofi_b)
    print(
        "\n解读: 若顶端 bucket net10 转正而低端为负，则证实'仅在脉冲/高波动时才盈利'。"
    )


if __name__ == "__main__":
    main()
