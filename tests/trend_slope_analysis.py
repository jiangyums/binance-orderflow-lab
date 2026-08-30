import csv
import bisect
import collections
import statistics
import glob

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


def add_local_trend(rows, W=60.0):
    gt = [r["timestamp"] for r in rows]
    gm = [r["mid"] for r in rows]
    for i, r in enumerate(rows):
        t0 = r["timestamp"] - W * 1000
        j = bisect.bisect_left(gt, t0)
        if j <= 0:
            r["_trend"] = 0.0
        else:
            base = gm[j - 1]
            r["_trend"] = (r["mid"] / base - 1.0) if base > 0 else 0.0
    return rows


def fwd_return(gt, gm, gs, t0, entry, sp0, side):
    idx = bisect.bisect_left(gt, t0 + HORIZON_MS)
    if idx >= len(gt):
        idx = len(gt) - 1
    gross = (gm[idx] - entry) / entry
    if side == "SHORT":
        gross = -gross
    cost = half_spread(sp0, entry) + half_spread(gs[idx], gm[idx]) + 2 * FEE
    return gross, gross - cost


def vol_gate(rows, vol_pct):
    vols = sorted(r["_vol"] for r in rows if r["_vol"] > 0)
    cut = vols[int(vol_pct * len(vols))] if vols else 999
    return [r for r in rows if r["_vol"] >= cut]


# 分桶边界（60s趋势的百分号）
BINS = [(-9, -2.0, "< -2.0%"), (-2.0, -1.0, "-2~-1%"),
        (-1.0, -0.5, "-1~-0.5%"), (-0.5, -0.2, "-0.5~-0.2%"),
        (-0.2, 0.2, "flat -0.2~0.2%"), (0.2, 0.5, "0.2~0.5%"),
        (0.5, 1.0, "0.5~1%"), (1.0, 2.0, "1~2%"), (2.0, 9, "> 2.0%")]


def collect(rows, gt, gm, gs, thr):
    """contratrend: 方向=-sign(trend); 记录每笔的 trend/gross/net"""
    out = []
    last = None
    for r in rows:
        if abs(r["tofi"]) < thr:
            last = "FLAT"; continue
        if r["_vol"] <= 0:
            continue
        dirn = "SHORT" if r["_trend"] > 0 else "LONG"
        if dirn == last:
            continue
        last = dirn
        g, net = fwd_return(gt, gm, gs, r["timestamp"], r["mid"], r.get("spread", 0.0), dirn)
        out.append((r["_trend"] * 100.0, dirn, g, net))
    return out


def main():
    files = sorted(glob.glob("data/features_v2_seg_*.csv"))
    all_recs = []
    for path in files:
        rows = load(path)
        add_rolling_vol(rows, W=5.0)
        add_local_trend(rows, W=60.0)
        gt = [r["timestamp"] for r in rows]
        gm = [r["mid"] for r in rows]
        gs = [r.get("spread", 0.0) for r in rows]
        sub = vol_gate(rows, 0.95)
        all_recs += collect(sub, gt, gm, gs, 0.10)

    # 先看整体分布
    trs = sorted(r[0] for r in all_recs)
    if trs:
        def pct(p):
            i = min(len(trs) - 1, int(p * len(trs)))
            return trs[i]
        print("60s趋势分布: min=%.3f%% p10=%.3f%% p50=%.3f%% p90=%.3f%% max=%.3f%%"
              % (trs[0], pct(0.1), pct(0.5), pct(0.9), trs[-1]))
    print()

    # 按倾斜度百分位分 9 桶（每桶样本量相近）
    all_recs.sort(key=lambda x: x[0])
    N = 9
    step = len(all_recs) / N
    print("%-18s %8s %8s %10s %10s" % ("trend bucket", "n", "win%", "net/trade", "gross/trade"))
    for k in range(N):
        lo_i = int(k * step)
        hi_i = int((k + 1) * step) if k < N - 1 else len(all_recs)
        rec = all_recs[lo_i:hi_i]
        if not rec:
            continue
        lo_t = rec[0][0]; hi_t = rec[-1][0]
        n = len(rec)
        wins = sum(1 for (tr, dn, g, net) in rec if g > 0)
        net = sum(net for (tr, dn, g, net) in rec) / n
        gross = sum(g for (tr, dn, g, net) in rec) / n
        label = "%.3f~%.3f%%" % (lo_t, hi_t)
        print("%-18s %8d %7.1f%% %+10.5f %+10.5f" % (label, n, wins / n * 100, net, gross))


if __name__ == "__main__":
    main()
