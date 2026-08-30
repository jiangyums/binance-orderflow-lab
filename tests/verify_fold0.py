import csv
import bisect
import collections
import statistics
import random

csv.field_size_limit(2_147_483_647)
FEE = 0.0004
SRC = "data/_snapshot_features.csv"


def half_spread(spread, mid):
    try:
        s = float(spread); m = float(mid)
    except (ValueError, TypeError):
        return 0.0
    if s <= 0 or m <= 0:
        return 0.0
    return s / (2.0 * m)


def load(path):
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                row["timestamp"] = int(row["timestamp"])
            except (ValueError, TypeError):
                continue
            for k in ("mid", "microprice", "spread", "obi1", "obi5", "obi10",
                      "ofi", "cvd", "bid_depth", "ask_depth",
                      "buy_breakout", "sell_breakout", "tofi"):
                try:
                    row[k] = float(row[k])
                except (ValueError, TypeError):
                    row[k] = 0.0
            rows.append(row)
    rows.sort(key=lambda x: x["timestamp"])
    return rows


def add_rolling_vol(rows, W=5.0):
    for i in range(1, len(rows)):
        m0 = rows[i - 1]["mid"]; m1 = rows[i]["mid"]
        rows[i]["_ret"] = (m1 / m0 - 1.0) if (m0 > 0 and m1 > 0) else 0.0
    dq = collections.deque()
    for i in range(len(rows)):
        t = rows[i]["timestamp"]
        if i > 0:
            dq.append((t, rows[i]["_ret"]))
        while dq and (t - dq[0][0]) > W * 1000:
            dq.popleft()
        vals = [v for _, v in dq]
        rows[i]["_vol"] = statistics.pstdev(vals) if len(vals) >= 5 else 0.0
    return rows


def percentile(vals, p):
    vals = sorted(vals)
    if not vals:
        return 0.0
    return vals[min(len(vals) - 1, int(p * len(vals)))]


def fwd_return(gt, gm, gs, t0, entry, sp0, side):
    idx = bisect.bisect_left(gt, t0 + 5000)
    if idx >= len(gt):
        idx = len(gt) - 1
    gross = (gm[idx] - entry) / entry
    if side == "SHORT":
        gross = -gross
    cost = half_spread(sp0, entry) + half_spread(gs[idx], gm[idx]) + 2 * FEE
    return gross, cost


def trades_dedup(subset, signal_fn, gt, gm, gs):
    out = []
    last = None
    for r in subset:
        side = signal_fn(r)
        if side in (None, "FLAT"):
            last = "FLAT"; continue
        if side == last:
            continue
        last = side
        g, c = fwd_return(gt, gm, gs, r["timestamp"], r["mid"], r.get("spread", 0.0), side)
        out.append((r["timestamp"], r["tofi"], r.get("_vol", 0), side, g, g - c))
    return out


def trades_every(subset, side_fn, gt, gm, gs):
    out = []
    for r in subset:
        side = side_fn(r)
        g, c = fwd_return(gt, gm, gs, r["timestamp"], r["mid"], r.get("spread", 0.0), side)
        out.append((r["timestamp"], r["tofi"], r.get("_vol", 0), side, g, g - c))
    return out


def summarize(label, trades):
    if not trades:
        print("%-22s n=  0" % label); return
    wins = sum(1 for t in trades if t[4] > 0)
    net = sum(t[5] for t in trades) / len(trades)
    mean_g = sum(t[4] for t in trades) / len(trades)
    print("%-22s n=%5d  win=%5.1f%%  meanGross=%+7.5f  net=%+7.5f"
          % (label, len(trades), wins / len(trades) * 100, mean_g, net))


def main():
    rows = load(SRC)
    add_rolling_vol(rows, W=5.0)
    n = len(rows)
    N = 8
    size = n // N
    block0 = rows[0:size]
    block1 = rows[size:2 * size]

    gt = [r["timestamp"] for r in rows]
    gm = [r["mid"] for r in rows]
    gs = [r.get("spread", 0.0) for r in rows]

    p95 = percentile([r["_vol"] for r in block0 if r["_vol"] > 0], 0.95)
    print("n =", n, " fold size =", size, " block0 vol p95 =", round(p95, 5))
    print("block0 span(min)=%.1f  block1 span(min)=%.1f"
          % ((block0[-1]["timestamp"] - block0[0]["timestamp"]) / 60000.0,
             (block1[-1]["timestamp"] - block1[0]["timestamp"]) / 60000.0))

    # chosen scheme for fold 0: vol95, T=0.500
    def scheme(r):
        if r.get("_vol", 0.0) < p95:
            return "FLAT"
        if abs(r["tofi"]) < 0.500:
            return "FLAT"
        return "LONG" if r["tofi"] > 0 else "SHORT"

    def negated(r):
        s = scheme(r)
        return "SHORT" if s == "LONG" else ("LONG" if s == "SHORT" else "FLAT")

    print("\n=== block1 (fold0 OUT-sample) trades with CHOSEN scheme (vol95 T=0.5) ===")
    tr = trades_dedup(block1, scheme, gt, gm, gs)
    print("count =", len(tr))
    for (t, tofi, vol, side, g, net) in tr:
        print("  t=%d tofi=%+.3f vol=%.5f %-5s gross=%+.5f %s"
              % (t % 100000, tofi, vol, side, g, "WIN" if g > 0 else "LOSS"))
    summarize("CHOSEN (vol95 T=.5)", tr)

    print("\n=== baselines on block1 (every-row, 5s fwd) ===")
    random.seed(42)
    summarize("always LONG", trades_every(block1, lambda r: "LONG", gt, gm, gs))
    summarize("always SHORT", trades_every(block1, lambda r: "SHORT", gt, gm, gs))
    summarize("random", trades_every(block1, lambda r: random.choice(["LONG", "SHORT"]), gt, gm, gs))
    summarize("CHOSEN NEGATED", trades_every(block1, negated, gt, gm, gs))

    print("\n=== in-sample block0 with same fix (global timeline) ===")
    summarize("CHOSEN (vol95 T=.5)", trades_dedup(block0, scheme, gt, gm, gs))


if __name__ == "__main__":
    main()
