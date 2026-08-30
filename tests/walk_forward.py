import csv
import bisect
import collections
import statistics
import copy

csv.field_size_limit(2_147_483_647)
FEE = 0.0004


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


def evaluate(rows, signal_fn):
    timestamps = [r["timestamp"] for r in rows]
    mids = [r["mid"] for r in rows]
    spreads = [r.get("spread", 0.0) for r in rows]
    last = None
    signals = []
    for r in rows:
        side = signal_fn(r)
        if side is None or side == "FLAT":
            last = "FLAT"
            continue
        if side == last:
            continue
        last = side
        signals.append((r["timestamp"], side, r["mid"], r.get("spread", 0.0)))
    out = {"n": 0, "wins": 0, "gross": 0.0, "cost": 0.0}
    for (t0, side, entry, sp) in signals:
        idx = bisect.bisect_left(timestamps, t0 + 5000)  # report 5s horizon
        if idx >= len(timestamps):
            idx = len(timestamps) - 1
        gross = (mids[idx] - entry) / entry
        if side == "SHORT":
            gross = -gross
        cost = half_spread(sp, entry) + half_spread(spreads[idx], mids[idx]) + 2 * FEE
        out["n"] += 1
        if gross > 0:
            out["wins"] += 1
        out["gross"] += gross
        out["cost"] += cost
    return out


def make_signal(tofi_floor, gate, p95):
    def f(r):
        if gate == "vol95" and r.get("_vol", 0.0) < p95:
            return "FLAT"
        tofi = r["tofi"]
        if abs(tofi) < tofi_floor:
            return "FLAT"
        return "LONG" if tofi > 0 else "SHORT"
    return f


def percentile(vals, p):
    vals = sorted(vals)
    if not vals:
        return 0.0
    return vals[min(len(vals) - 1, int(p * len(vals)))]


CANDIDATES = []
for gate in ("none", "vol95"):
    for thr in (0.002, 0.01, 0.05, 0.1, 0.5):
        CANDIDATES.append((gate, thr))


def main(src):
    rows = load(src)
    add_rolling_vol(rows, W=5.0)
    n = len(rows)
    N = 8
    size = n // N
    blocks = [rows[i * size:(i + 1) * size] for i in range(N)]

    print("walk-forward on", src, " rows =", n, " folds =", N,
          " (~%.1f min each)" % ((size / 21.6) / 60.0))
    print()
    print("%-5s %-9s %-7s | %-22s | %-22s"
          % ("fold", "trainWin", "chosen", "IN-sample (net/gross)", "OUT-sample (net/gross)"))
    print("-" * 88)

    agg_in = {"n": 0, "wins": 0, "gross": 0.0, "cost": 0.0}
    agg_out = {"n": 0, "wins": 0, "gross": 0.0, "cost": 0.0}

    for i in range(N - 1):
        train = [r for b in blocks[:i + 1] for r in b]
        test = blocks[i + 1]
        p95 = percentile([r["_vol"] for r in train if r["_vol"] > 0], 0.95)
        best = None
        for gate, thr in CANDIDATES:
            res = evaluate(train, make_signal(thr, gate, p95))
            if res["n"] == 0:
                continue
            net = res["gross"] / res["n"] - res["cost"] / res["n"]
            if best is None or net > best[0]:
                best = (net, gate, thr, res)
        if best is None:
            continue
        _, gate, thr, inres = best
        outres = evaluate(test, make_signal(thr, gate, p95))
        win_in = inres["wins"] / inres["n"] if inres["n"] else 0
        net_in = inres["gross"] / inres["n"] - inres["cost"] / inres["n"]
        if outres["n"]:
            win_out = outres["wins"] / outres["n"]
            net_out = outres["gross"] / outres["n"] - outres["cost"] / outres["n"]
        else:
            win_out = 0.0
            net_out = 0.0
        print("%-5d %-9d %-7sT=%.3f | net=%+.5f win=%4.1f%% n=%5d | net=%+.5f win=%4.1f%% n=%5d"
              % (i, (i + 1) * size, gate + " ", thr,
                 net_in, win_in * 100, inres["n"],
                 net_out, win_out * 100, outres["n"]))
        for d, res in ((agg_in, inres), (agg_out, outres)):
            d["n"] += res["n"]; d["wins"] += res["wins"]
            d["gross"] += res["gross"]; d["cost"] += res["cost"]

    print("-" * 88)
    if agg_in["n"]:
        print("AGG IN-sample : net=%+.5f  win=%4.1f%%  n=%d"
              % (agg_in["gross"] / agg_in["n"] - agg_in["cost"] / agg_in["n"],
                 agg_in["wins"] / agg_in["n"] * 100, agg_in["n"]))
    if agg_out["n"]:
        print("AGG OUT-sample: net=%+.5f  win=%4.1f%%  n=%d   <-- 真实无偏估计"
              % (agg_out["gross"] / agg_out["n"] - agg_out["cost"] / agg_out["n"],
                 agg_out["wins"] / agg_out["n"] * 100, agg_out["n"]))


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "data/features.csv")
