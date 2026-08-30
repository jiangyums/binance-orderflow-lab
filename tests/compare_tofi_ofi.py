import csv
import bisect
import collections
import statistics
import sys

csv.field_size_limit(2_147_483_647)
FEE = 0.0004
SRC = sys.argv[1] if len(sys.argv) > 1 else "data/_snapshot_features.csv"

# horizon for forward return: argv[2] like "1s", "5s", "10s"
_HORIZON_ARG = sys.argv[2] if len(sys.argv) > 2 else "5s"
HORIZON_MS = int(_HORIZON_ARG.replace("s", "")) * 1000


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


def summarize(label, tr):
    if not tr:
        print("%-10s n=  0" % label); return
    n = len(tr)
    wins = sum(1 for t in tr if t[2] > 0)
    g = sum(t[2] for t in tr) / n
    net = sum(t[3] for t in tr) / n
    print("%-10s n=%6d  win=%5.1f%%  gross=%+8.5f  net=%+8.5f"
          % (label, n, wins / n * 100, g, net))


def side_split(label, tr):
    longs = [t for t in tr if t[1] == "LONG"]
    shorts = [t for t in tr if t[1] == "SHORT"]
    summarize(label + " ALL  ", tr)
    summarize(label + " LONG ", longs)
    summarize(label + " SHORT", shorts)


def quantile_buckets(tr):
    absv = sorted(abs(t[0]) for t in tr)
    edges = [0.5, 0.75, 0.9, 0.99]
    cuts = [absv[int(e * len(absv))] for e in edges]
    labels = ["0-50%", "50-75%", "75-90%", "90-99%", "99-100%"]
    buckets = [[] for _ in range(5)]
    for t in tr:
        a = abs(t[0])
        if a <= cuts[0]:
            buckets[0].append(t)
        elif a <= cuts[1]:
            buckets[1].append(t)
        elif a <= cuts[2]:
            buckets[2].append(t)
        elif a <= cuts[3]:
            buckets[3].append(t)
        else:
            buckets[4].append(t)
    return labels, buckets


def vol_gate(rows, vol_pct):
    vols = sorted(r["_vol"] for r in rows if r["_vol"] > 0)
    cut = vols[int(vol_pct * len(vols))] if vols else 999
    return [r for r in rows if r["_vol"] >= cut]


def main():
    rows = load(SRC)
    add_rolling_vol(rows, W=5.0)
    gt = [r["timestamp"] for r in rows]
    gm = [r["mid"] for r in rows]
    gs = [r.get("spread", 0.0) for r in rows]
    print("source:", SRC, " rows =", len(rows))
    print("method: sign(signal)->LONG/SHORT, dedup side-change, %ds fwd, net=fee(.0008)+half-spread\n"
          % (HORIZON_MS // 1000))

    for col, name in (("tofi", "TOFI "), ("ofi", "OFI  ")):
        tr = trades(rows, col, gt, gm, gs, floor=0.0)
        print("===== %s (threshold=0, pure sign) =====" % name)
        side_split(name, tr)
        labels, buckets = quantile_buckets(tr)
        print("  -- by |%s| strength (quantile) --" % col)
        for lab, b in zip(labels, buckets):
            if b:
                n = len(b); w = sum(1 for t in b if t[2] > 0) / n
                g = sum(t[2] for t in b) / n
                print("    %-8s n=%6d win=%5.1f%% gross=%+8.5f" % (lab, n, w * 100, g))
        print()

    print("=" * 70)
    print("VOLATILITY GATE (5s window, only trade when vol >= percentile)")
    print("=" * 70)
    for vol_pct in (0.90, 0.95, 0.99):
        sub = vol_gate(rows, vol_pct)
        if len(sub) < 20:
            continue
        print("\n--- vol >= p%d (%d rows, %.1f%% of total) ---" %
              (int(vol_pct * 100), len(sub), 100 * len(sub) / len(rows)))
        for col, name in (("tofi", "TOFI "), ("ofi", "OFI  ")):
            tr = trades(sub, col, gt, gm, gs, floor=0.0)
            side_split(name, tr)
        print()

    print("=" * 70)
    print("TOFI THRESHOLD SWEEP (no vol gate)")
    print("=" * 70)
    print("%-8s %5s  %5s  %6s  %5s  %9s  %9s" % ("thr", "n", "n/L", "n/S", "win%", "gross", "net"))
    for tofi_thr in (0.0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50):
        tr = trades(rows, "tofi", gt, gm, gs, floor=tofi_thr)
        n = len(tr)
        if n < 5:
            continue
        wins = sum(1 for t in tr if t[2] > 0)
        g = sum(t[2] for t in tr) / n
        net = sum(t[3] for t in tr) / n
        longs = [t for t in tr if t[1] == "LONG"]
        shorts = [t for t in tr if t[1] == "SHORT"]
        print("%-8s %5d  %5d  %6d  %5.1f%%  %+9.5f  %+9.5f"
              % ("%.2f" % tofi_thr, n, len(longs), len(shorts), wins / n * 100, g, net))

    print()
    print("%-8s %5s  %5s  %6s  %5s  %9s  %9s  %9s  %9s" %
          ("thr", "n", "n/L", "n/S", "win%", "g_ALL", "net_ALL", "g_SHORT", "net_SHORT"))
    for tofi_thr in (0.0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50):
        tr = trades(rows, "tofi", gt, gm, gs, floor=tofi_thr)
        n = len(tr)
        if n < 5:
            continue
        wins = sum(1 for t in tr if t[2] > 0)
        g = sum(t[2] for t in tr) / n
        net = sum(t[3] for t in tr) / n
        shorts = [t for t in tr if t[1] == "SHORT"]
        g_s = sum(t[2] for t in shorts) / len(shorts) if shorts else 0
        net_s = sum(t[3] for t in shorts) / len(shorts) if shorts else 0
        print("%-8s %5d  %5d  %6d  %5.1f%%  %+9.5f  %+9.5f  %+9.5f  %+9.5f"
              % ("%.2f" % tofi_thr, n, len([t for t in tr if t[1]=="LONG"]),
                 len(shorts), wins / n * 100, g, net, g_s, net_s))

    print()
    print("=" * 70)
    print("COMBO: tofi_threshold + vol gate")
    print("=" * 70)
    for vol_pct in (0.90, 0.95):
        print("\n--- vol >= p%d ---" % int(vol_pct * 100))
        sub = vol_gate(rows, vol_pct)
        print("%-8s %5s  %5s  %6s  %5s  %6s  %6s  %9s  %9s  %9s  %9s  %9s  %9s" %
              ("thr", "n", "n/L", "n/S", "win%", "w_L%", "w_S%", "g_ALL", "net_ALL",
               "g_LONG", "net_LONG", "g_SHORT", "net_SHORT"))
        for tofi_thr in (0.0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50):
            tr = trades(sub, "tofi", gt, gm, gs, floor=tofi_thr)
            n = len(tr)
            if n < 5:
                continue
            wins = sum(1 for t in tr if t[2] > 0)
            g = sum(t[2] for t in tr) / n
            net = sum(t[3] for t in tr) / n
            longs = [t for t in tr if t[1] == "LONG"]
            shorts = [t for t in tr if t[1] == "SHORT"]
            win_l = sum(1 for t in longs if t[2] > 0) / len(longs) * 100 if longs else 0
            win_s = sum(1 for t in shorts if t[2] > 0) / len(shorts) * 100 if shorts else 0
            g_l = sum(t[2] for t in longs) / len(longs) if longs else 0
            net_l = sum(t[3] for t in longs) / len(longs) if longs else 0
            g_s = sum(t[2] for t in shorts) / len(shorts) if shorts else 0
            net_s = sum(t[3] for t in shorts) / len(shorts) if shorts else 0
            print("%-8s %5d  %5d  %6d  %5.1f%% %5.1f%% %5.1f%% %+9.5f  %+9.5f  %+9.5f  %+9.5f  %+9.5f  %+9.5f"
                  % ("%.2f" % tofi_thr, n, len(longs), len(shorts), wins / n * 100,
                     win_l, win_s, g, net, g_l, net_l, g_s, net_s))

    print()
    print("=" * 70)
    print("COMBO: ofi_threshold + vol gate")
    print("=" * 70)
    for vol_pct in (0.90, 0.95):
        print("\n--- vol >= p%d ---" % int(vol_pct * 100))
        sub = vol_gate(rows, vol_pct)
        print("%-8s %5s  %5s  %6s  %5s  %6s  %6s  %9s  %9s  %9s  %9s" %
              ("thr", "n", "n/L", "n/S", "win%", "w_L%", "w_S%", "g_ALL", "net_ALL",
               "g_SHORT", "net_SHORT"))
        for ofi_thr in (0.0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50):
            tr = trades(sub, "ofi", gt, gm, gs, floor=ofi_thr)
            n = len(tr)
            if n < 5:
                continue
            wins = sum(1 for t in tr if t[2] > 0)
            g = sum(t[2] for t in tr) / n
            net = sum(t[3] for t in tr) / n
            longs = [t for t in tr if t[1] == "LONG"]
            shorts = [t for t in tr if t[1] == "SHORT"]
            win_l = sum(1 for t in longs if t[2] > 0) / len(longs) * 100 if longs else 0
            win_s = sum(1 for t in shorts if t[2] > 0) / len(shorts) * 100 if shorts else 0
            g_s = sum(t[2] for t in shorts) / len(shorts) if shorts else 0
            net_s = sum(t[3] for t in shorts) / len(shorts) if shorts else 0
            print("%-8s %5d  %5d  %6d  %5.1f%% %5.1f%% %5.1f%% %+9.5f  %+9.5f  %+9.5f  %+9.5f"
                  % ("%.2f" % ofi_thr, n, len(longs), len(shorts), wins / n * 100,
                     win_l, win_s, g, net, g_s, net_s))

    print()
    print("=" * 70)
    print("CONFLUENCE: tofi & ofi same direction")
    print("=" * 70)
    for vol_pct in (0.0, 0.90, 0.95):
        sub = rows if vol_pct == 0.0 else vol_gate(rows, vol_pct)
        label = "no vol gate" if vol_pct == 0.0 else "vol>=p%d" % int(vol_pct * 100)
        print("\n--- %s (%d rows) ---" % (label, len(sub)))
        gt_sub = [r["timestamp"] for r in sub]
        gm_sub = [r["mid"] for r in sub]
        gs_sub = [r.get("spread", 0.0) for r in sub]

        for col_a, col_b, label_ab in (("tofi", "ofi", "tofi & ofi"),):
            out = []
            last = None
            for r in sub:
                va = r.get(col_a, 0.0)
                vb = r.get(col_b, 0.0)
                if va == 0.0 or vb == 0.0:
                    last = "FLAT"; continue
                if va * vb <= 0:
                    last = "FLAT"; continue
                side = "LONG" if va > 0 else "SHORT"
                if side == last:
                    continue
                last = side
                g, c = fwd_return(gt_sub, gm_sub, gs_sub, r["timestamp"], r["mid"],
                                  r.get("spread", 0.0), side)
                out.append((va, side, g, g - c))

            n = len(out)
            if n < 5:
                continue
            wins = sum(1 for t in out if t[2] > 0)
            g = sum(t[2] for t in out) / n
            net = sum(t[3] for t in out) / n
            longs = [t for t in out if t[1] == "LONG"]
            shorts = [t for t in out if t[1] == "SHORT"]
            g_l = sum(t[2] for t in longs) / len(longs) if longs else 0
            net_l = sum(t[3] for t in longs) / len(longs) if longs else 0
            g_s = sum(t[2] for t in shorts) / len(shorts) if shorts else 0
            net_s = sum(t[3] for t in shorts) / len(shorts) if shorts else 0
            print("%-12s n=%5d  win=%5.1f%%  g=%+8.5f  net=%+8.5f" %
                  (label_ab, n, wins / n * 100, g, net))
            print("  LONG  n=%5d  win=%5.1f%%  g=%+8.5f  net=%+8.5f" %
                  (len(longs), 100 * sum(1 for t in longs if t[2]>0)/len(longs) if longs else 0,
                   g_l, net_l))
            print("  SHORT n=%5d  win=%5.1f%%  g=%+8.5f  net=%+8.5f" %
                  (len(shorts), 100 * sum(1 for t in shorts if t[2]>0)/len(shorts) if shorts else 0,
                   g_s, net_s))

    print()
    print("=" * 70)
    print("CONFLUENCE: tofi & ofi same direction + tofi threshold")
    print("=" * 70)
    for vol_pct in (0.90, 0.95):
        sub = vol_gate(rows, vol_pct)
        print("\n--- vol >= p%d ---" % int(vol_pct * 100))
        gt_sub = [r["timestamp"] for r in sub]
        gm_sub = [r["mid"] for r in sub]
        gs_sub = [r.get("spread", 0.0) for r in sub]
        for tofi_thr in (0.0, 0.02, 0.05, 0.10, 0.20):
            out = []
            last = None
            for r in sub:
                va = r.get("tofi", 0.0)
                vb = r.get("ofi", 0.0)
                if abs(va) < tofi_thr or vb == 0.0:
                    last = "FLAT"; continue
                if va * vb <= 0:
                    last = "FLAT"; continue
                side = "LONG" if va > 0 else "SHORT"
                if side == last:
                    continue
                last = side
                g, c = fwd_return(gt_sub, gm_sub, gs_sub, r["timestamp"], r["mid"],
                                  r.get("spread", 0.0), side)
                out.append((va, side, g, g - c))
            n = len(out)
            if n < 5:
                continue
            wins = sum(1 for t in out if t[2] > 0)
            g = sum(t[2] for t in out) / n
            net = sum(t[3] for t in out) / n
            shorts = [t for t in out if t[1] == "SHORT"]
            g_s = sum(t[2] for t in shorts) / len(shorts) if shorts else 0
            net_s = sum(t[3] for t in shorts) / len(shorts) if shorts else 0
            print("tofi>=%.2f  n=%4d  win=%5.1f%%  g=%+8.5f  net=%+8.5f  SHORT: n=%3d g=%+8.5f net=%+8.5f"
                  % (tofi_thr, n, wins / n * 100, g, net,
                     len(shorts), g_s, net_s))


if __name__ == "__main__":
    main()
