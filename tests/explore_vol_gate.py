import csv
import bisect
import collections
import statistics

csv.field_size_limit(2_147_483_647)

FEE = 0.0004  # per-side fee fraction


def half_spread(spread, mid):
    try:
        s = float(spread)
        m = float(mid)
    except (ValueError, TypeError):
        return 0.0
    if s <= 0 or m <= 0:
        return 0.0
    return s / (2.0 * m)


def load(path):
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                row["timestamp"] = int(row["timestamp"])
            except (ValueError, TypeError):
                continue
            for k in (
                "mid", "microprice", "spread", "obi1", "obi5", "obi10",
                "ofi", "cvd", "bid_depth", "ask_depth",
                "buy_breakout", "sell_breakout", "tofi",
            ):
                try:
                    row[k] = float(row[k])
                except (ValueError, TypeError):
                    row[k] = 0.0
            rows.append(row)
    rows.sort(key=lambda x: x["timestamp"])
    return rows


def add_rolling_vol(rows, W=5.0):
    """Causal rolling std of mid-returns over the trailing W seconds."""
    for i in range(1, len(rows)):
        m0 = rows[i - 1]["mid"]
        m1 = rows[i]["mid"]
        rows[i]["_ret"] = (m1 / m0 - 1.0) if (m0 > 0 and m1 > 0) else 0.0
    dq = collections.deque()
    for i in range(len(rows)):
        t = rows[i]["timestamp"]
        if i > 0:
            dq.append(rows[i]["_ret"])
        while dq and (t - dq[0] if False else (t - rows[i - len(dq) + 1]["timestamp"] if dq else 0)) > W * 1000:
            dq.popleft()
        # simpler: track timestamps alongside
        pass
    # redo cleanly with (ts, ret) pairs
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
        wins = 0
        sret = 0.0
        scost = 0.0
        cnt = 0
        for (t0, side, entry, sp) in signals:
            idx = bisect.bisect_left(timestamps, t0 + H)
            if idx >= len(timestamps):
                continue
            exit_m = mids[idx]
            exit_sp = spreads[idx]
            gross = (exit_m - entry) / entry
            if side == "SHORT":
                gross = -gross
            cost = half_spread(sp, entry) + half_spread(exit_sp, exit_m) + 2 * FEE
            cnt += 1
            if gross > 0:
                wins += 1
            sret += gross
            scost += cost
        if cnt:
            out["n" + key] = cnt
            out["win" + key] = wins / cnt
            out["ret" + key] = sret / cnt
            out["net" + key] = sret / cnt - scost / cnt
        else:
            out["n" + key] = 0
            out["win" + key] = 0.0
            out["ret" + key] = 0.0
            out["net" + key] = 0.0
    return out


def make_vol_gate(tofi_floor, vol_thr):
    def f(r):
        if r.get("_vol", 0.0) < vol_thr:
            return "FLAT"
        tofi = r["tofi"]
        if abs(tofi) < tofi_floor:
            return "FLAT"
        return "LONG" if tofi > 0 else "SHORT"
    return f


def make_trade_ofi(t):
    def f(r):
        tofi = r["tofi"]
        if tofi > t:
            return "LONG"
        if tofi < -t:
            return "SHORT"
        return "FLAT"
    return f


def percentile(vals, p):
    vals = sorted(vals)
    if not vals:
        return 0.0
    i = min(len(vals) - 1, int(p * len(vals)))
    return vals[i]


def main():
    rows = load("data/features.csv")
    add_rolling_vol(rows, W=5.0)
    vols = [r["_vol"] for r in rows if r["_vol"] > 0]
    print("rows =", len(rows))
    print("vol percentiles: p50=%.5f p75=%.5f p90=%.5f p95=%.5f max=%.5f"
          % (percentile(vols, 0.5), percentile(vols, 0.75),
             percentile(vols, 0.9), percentile(vols, 0.95), max(vols)))
    print()

    # Diagnostic: does |forward 5s return| actually grow with vol?
    buckets = [(0.0, "all"), (percentile(vols, 0.5), "vol>=p50"),
               (percentile(vols, 0.75), "vol>=p75"), (percentile(vols, 0.9), "vol>=p90")]
    print("=== diagnostic: avg |fwd 5s return| by vol bucket (trade-OFI signals) ===")
    for thr, label in buckets:
        sig = make_vol_gate(0.002, thr)
        # compute avg |fwd5| over emitted signals manually
        ts = [r["timestamp"] for r in rows]
        mids = [r["mid"] for r in rows]
        last = None
        tot = 0.0
        cnt = 0
        sgn = 0.0
        for r in rows:
            side = sig(r)
            if side is None or side == "FLAT":
                last = "FLAT"
                continue
            if side == last:
                continue
            last = side
            idx = bisect.bisect_left(ts, r["timestamp"] + 5000)
            if idx >= len(ts):
                continue
            g = (mids[idx] - r["mid"]) / r["mid"]
            tot += abs(g)
            sgn += (g if side == "LONG" else -g)
            cnt += 1
        if cnt:
            print("  %-10s n=%-5d  avg|fwd5|=%.5f  signed_avg=%.5f"
                  % (label, cnt, tot / cnt, sgn / cnt))
    print()

    print("%-30s %6s %6s %6s | %7s %7s %7s | %8s %8s %8s"
          % ("scheme", "n1", "n5", "n10", "win1%", "win5%", "win10%", "net1", "net5", "net10"))
    print("-" * 92)

    # baseline
    for t in [0.0, 0.002]:
        o = evaluate(rows, make_trade_ofi(t))
        print("%-30s %6d %6d %6d | %6.1f%% %6.1f%% %6.1f%% | %+7.5f %+7.5f %+7.5f"
              % ("trade_ofi t=%.3f (no gate)" % t, o["n1"], o["n5"], o["n10"],
                 o["win1"] * 100, o["win5"] * 100, o["win10"] * 100,
                 o["net1"], o["net5"], o["net10"]))

    for p in [0.5, 0.75, 0.9, 0.95]:
        thr = percentile(vols, p)
        o = evaluate(rows, make_vol_gate(0.002, thr))
        print("%-30s %6d %6d %6d | %6.1f%% %6.1f%% %6.1f%% | %+7.5f %+7.5f %+7.5f"
              % ("vol_gate>=p%02d (t_floor=.002)" % int(p * 100), o["n1"], o["n5"], o["n10"],
                 o["win1"] * 100, o["win5"] * 100, o["win10"] * 100,
                 o["net1"], o["net5"], o["net10"]))


if __name__ == "__main__":
    main()
