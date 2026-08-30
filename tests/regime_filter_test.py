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


def trades_cond(rows, gt, gm, gs, thr, mode):
    """mode:
       'follow'          = 方向=sign(local_trend)
       'contratrend'     = 方向=-sign(local_trend)，tofi方向忽略
       'flow_contratrend'= 仅当 sign(tofi)!=sign(trend) 才做，方向=sign(tofi)
    """
    out = []
    last = None
    for r in rows:
        if abs(r["tofi"]) < thr:
            last = "FLAT"; continue
        if r["_vol"] <= 0:
            continue
        if mode == "follow":
            dirn = "LONG" if r["_trend"] > 0 else "SHORT"
        elif mode == "contratrend":
            dirn = "SHORT" if r["_trend"] > 0 else "LONG"
        else:  # flow_contratrend
            # flow 与趋势同向 -> 跳过
            if (r["_trend"] > 0 and r["tofi"] > 0) or (r["_trend"] < 0 and r["tofi"] < 0):
                last = "FLAT"; continue
            dirn = "LONG" if r["tofi"] > 0 else "SHORT"
        if dirn == last:
            continue
        last = dirn
        g, net = fwd_return(gt, gm, gs, r["timestamp"], r["mid"], r.get("spread", 0.0), dirn)
        out.append((dirn, g, net))
    return out


def vol_gate(rows, vol_pct):
    vols = sorted(r["_vol"] for r in rows if r["_vol"] > 0)
    cut = vols[int(vol_pct * len(vols))] if vols else 999
    return [r for r in rows if r["_vol"] >= cut]


def summ(tr):
    if not tr:
        return (0, 0.0, 0.0)
    n = len(tr)
    wins = sum(1 for t in tr if t[1] > 0)
    net = sum(t[2] for t in tr) / n
    return (n, wins / n * 100, net)


def main():
    files = sorted(glob.glob("data/features_v2_seg_*.csv"))
    print("%-22s | %10s | %12s | %14s" %
          ("segment", "follow", "contratrend", "flow_contratrend"))
    print("%-22s | %9s %7s | %11s %9s | %13s %11s" %
          ("", "net", "win%", "net", "win%", "net", "win%"))
    fo_all = []; cf_all = []; fc_all = []
    for path in files:
        rows = load(path)
        add_rolling_vol(rows, W=5.0)
        add_local_trend(rows, W=60.0)
        gt = [r["timestamp"] for r in rows]
        gm = [r["mid"] for r in rows]
        gs = [r.get("spread", 0.0) for r in rows]
        sub = vol_gate(rows, 0.95)
        fo = trades_cond(sub, gt, gm, gs, 0.10, "follow")
        cf = trades_cond(sub, gt, gm, gs, 0.10, "contratrend")
        fc = trades_cond(sub, gt, gm, gs, 0.10, "flow_contratrend")
        n1, w1, net1 = summ(fo)
        n2, w2, net2 = summ(cf)
        n3, w3, net3 = summ(fc)
        fo_all += fo; cf_all += cf; fc_all += fc
        print("%-22s | %+9.5f %6.1f | %+11.5f %8.1f | %+13.5f %10.1f" %
              (path.split("/")[-1], net1, w1, net2, w2, net3, w3))

    n1, w1, net1 = summ(fo_all)
    n2, w2, net2 = summ(cf_all)
    n3, w3, net3 = summ(fc_all)
    print("\n%-22s | %+9.5f %6.1f | %+11.5f %8.1f | %+13.5f %10.1f" %
          ("ALL-COMBINED", net1, w1, net2, w2, net3, w3))


if __name__ == "__main__":
    main()
