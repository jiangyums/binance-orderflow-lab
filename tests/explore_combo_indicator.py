import csv
import bisect
import collections
import statistics

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
    out = {}
    for H, key in ((1000, "1"), (5000, "5"), (10000, "10")):
        wins = sret = scost = cnt = 0
        for (t0, side, entry, sp) in signals:
            idx = bisect.bisect_left(timestamps, t0 + H)
            if idx >= len(timestamps):
                continue
            gross = (mids[idx] - entry) / entry
            if side == "SHORT":
                gross = -gross
            cost = half_spread(sp, entry) + half_spread(spreads[idx], mids[idx]) + 2 * FEE
            cnt += 1
            if gross > 0:
                wins += 1
            sret += gross
            scost += cost
        if cnt:
            out["n" + key] = cnt
            out["win" + key] = wins / cnt
            out["net" + key] = sret / cnt - scost / cnt
        else:
            out["n" + key] = out["win" + key] = out["net" + key] = 0
    return out


def make_trade_ofi(tofi_floor):
    def f(r):
        tofi = r["tofi"]
        if tofi > tofi_floor:
            return "LONG"
        if tofi < -tofi_floor:
            return "SHORT"
        return "FLAT"
    return f


def make_vol_gate(tofi_floor, vol_thr):
    def f(r):
        if r.get("_vol", 0.0) < vol_thr:
            return "FLAT"
        tofi = r["tofi"]
        if abs(tofi) < tofi_floor:
            return "FLAT"
        return "LONG" if tofi > 0 else "SHORT"
    return f


def make_combo_switch(alpha, tofi_floor, ofi_floor, vol_thr):
    # Follow trade-OFI when |tofi| >= alpha*|ofi| (trade flow dominant),
    # otherwise follow book-OFI. Both gated by volatility.
    def f(r):
        if r.get("_vol", 0.0) < vol_thr:
            return "FLAT"
        tofi = r["tofi"]; ofi = r["ofi"]
        if ofi == 0:
            if abs(tofi) < tofi_floor:
                return "FLAT"
            return "LONG" if tofi > 0 else "SHORT"
        if abs(tofi) >= alpha * abs(ofi):
            if abs(tofi) < tofi_floor:
                return "FLAT"
            return "LONG" if tofi > 0 else "SHORT"
        else:
            if abs(ofi) < ofi_floor:
                return "FLAT"
            return "LONG" if ofi > 0 else "SHORT"
    return f


def make_combo_blend(st, so, vol_thr, score_floor=0.1):
    # Additive normalized blend of the two flow directions.
    def f(r):
        if r.get("_vol", 0.0) < vol_thr:
            return "FLAT"
        tofi = r["tofi"]; ofi = r["ofi"]
        s = (1 if tofi > 0 else -1) * min(abs(tofi) / st, 1.0) + \
            (1 if ofi > 0 else -1) * min(abs(ofi) / so, 1.0)
        if abs(s) < score_floor:
            return "FLAT"
        return "LONG" if s > 0 else "SHORT"
    return f


def percentile(vals, p):
    vals = sorted(vals)
    if not vals:
        return 0.0
    return vals[min(len(vals) - 1, int(p * len(vals)))]


def main():
    rows = load("data/features.csv")
    add_rolling_vol(rows, W=5.0)
    vols = [r["_vol"] for r in rows if r["_vol"] > 0]
    p95 = percentile(vols, 0.95)
    print("rows =", len(rows), " vol p95 =", round(p95, 5))
    print()
    print("%-34s %6s %6s %6s | %7s %7s %7s | %8s %8s %8s"
          % ("scheme", "n1", "n5", "n10", "win1%", "win5%", "win10%", "net1", "net5", "net10"))
    print("-" * 92)

    # Baseline: best so far
    o = evaluate(rows, make_vol_gate(0.05, p95))
    print("%-34s %6d %6d %6d | %6.1f%% %6.1f%% %6.1f%% | %+7.5f %+7.5f %+7.5f"
          % ("BASE trade_ofi thr=.05 +vol>=p95", o["n1"], o["n5"], o["n10"],
             o["win1"] * 100, o["win5"] * 100, o["win10"] * 100,
             o["net1"], o["net5"], o["net10"]))

    # Dominant-flow switch
    for a in [0.02, 0.05, 0.1, 0.5]:
        o = evaluate(rows, make_combo_switch(a, 0.05, 0.1, p95))
        print("%-34s %6d %6d %6d | %6.1f%% %6.1f%% %6.1f%% | %+7.5f %+7.5f %+7.5f"
              % ("switch a=%.2f +vol>=p95" % a, o["n1"], o["n5"], o["n10"],
                 o["win1"] * 100, o["win5"] * 100, o["win10"] * 100,
                 o["net1"], o["net5"], o["net10"]))

    # Additive blend
    for st, so in [(0.05, 2.0), (0.05, 5.0)]:
        o = evaluate(rows, make_combo_blend(st, so, p95))
        print("%-34s %6d %6d %6d | %6.1f%% %6.1f%% %6.1f%% | %+7.5f %+7.5f %+7.5f"
              % ("blend st=%.2f so=%.1f +vol" % (st, so), o["n1"], o["n5"], o["n10"],
                 o["win1"] * 100, o["win5"] * 100, o["win10"] * 100,
                 o["net1"], o["net5"], o["net10"]))


if __name__ == "__main__":
    main()
