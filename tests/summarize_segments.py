import csv
import bisect
import collections
import statistics
import sys

csv.field_size_limit(2_147_483_647)
FEE = 0.0004
HORIZON_MS = 5000


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
            for k in ("mid", "spread", "ofi", "tofi"):
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


def fwd_return(gt, gm, gs, t0, entry, sp0, side):
    idx = bisect.bisect_left(gt, t0 + HORIZON_MS)
    if idx >= len(gt):
        idx = len(gt) - 1
    gross = (gm[idx] - entry) / entry
    if side == "SHORT":
        gross = -gross
    cost = half_spread(sp0, entry) + half_spread(gs[idx], gm[idx]) + 2 * FEE
    return gross, cost


def trades(rows, col, gt, gm, gs, floor=0.0):
    out = []
    last = None
    for r in rows:
        v = r.get(col, 0.0)
        if v == 0.0 or abs(v) < floor:
            last = "FLAT"; continue
        side = "LONG" if v > 0 else "SHORT"
        if side == last:
            continue
        last = side
        g, c = fwd_return(gt, gm, gs, r["timestamp"], r["mid"], r.get("spread", 0.0), side)
        out.append((r[col], side, g, g - c))
    return out


def vol_gate(rows, vol_pct):
    vols = sorted(r["_vol"] for r in rows if r["_vol"] > 0)
    cut = vols[int(vol_pct * len(vols))] if vols else 999
    return [r for r in rows if r["_vol"] >= cut]


def summarize(tr):
    if not tr:
        return (0, 0.0, 0.0)
    n = len(tr)
    wins = sum(1 for t in tr if t[2] > 0)
    net = sum(t[3] for t in tr) / n
    return (n, wins / n * 100, net)


def main():
    files = sorted([f for f in __import__("glob").glob("data/features_v2_seg_*.csv")])
    print("%-22s %9s %8s %8s %8s %8s %8s %8s" %
          ("segment", "trend%", "n(L)", "netL", "n(S)", "netS", "best", "align"))
    align = 0; tot = 0
    for path in files:
        rows = load(path)
        add_rolling_vol(rows, W=5.0)
        gt = [r["timestamp"] for r in rows]
        gm = [r["mid"] for r in rows]
        gs = [r.get("spread", 0.0) for r in rows]
        sub = vol_gate(rows, 0.95)
        tr = trades(sub, "tofi", gt, gm, gs, floor=0.0)
        longs = [t for t in tr if t[1] == "LONG"]
        shorts = [t for t in tr if t[1] == "SHORT"]
        nL, wL, netL = summarize(longs)
        nS, wS, netS = summarize(shorts)
        best = "LONG" if netL > netS else "SHORT"
        # 段级趋势：首末 mid
        trend = (rows[-1]["mid"] / rows[0]["mid"] - 1.0) * 100.0 if rows[0]["mid"] > 0 else 0.0
        # 假设：顺势(趋势向上则做多LONG赢) -> best==LONG 且 trend>0, 或 best==SHORT 且 trend<0
        aligned = (best == "LONG" and trend > 0) or (best == "SHORT" and trend < 0)
        if aligned:
            align += 1
        tot += 1
        print("%-22s %+9.3f %8d %+8.5f %8d %+8.5f %8s %8s" %
              (path.split("/")[-1], trend, nL, netL, nS, netS, best,
               "YES" if aligned else "no"))
    print("\ntrend-alignment: %d/%d (random=5/10)" % (align, tot))


if __name__ == "__main__":
    main()
