import csv
import bisect

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


def main():
    rows = []
    with open("data/features.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            try:
                rows.append({
                    "ts": int(r["timestamp"]),
                    "mid": float(r["mid"]),
                    "tofi": float(r.get("tofi", "0")),
                    "spread": float(r.get("spread", "0")),
                })
            except (ValueError, TypeError):
                pass
    rows.sort(key=lambda x: x["ts"])
    gt = [r["ts"] for r in rows]
    gm = [r["mid"] for r in rows]

    trades = []
    last = None
    for r in rows:
        v = r["tofi"]
        if v == 0:
            last = "FLAT"; continue
        side = "LONG" if v > 0 else "SHORT"
        if side == last:
            continue
        last = side
        av = abs(v)
        rets = {}
        for hz_ms, hz_name in ((1000, "1s"), (5000, "5s"), (10000, "10s")):
            idx = bisect.bisect_left(gt, r["ts"] + hz_ms)
            if idx >= len(rows):
                idx = len(rows) - 1
            gross = (gm[idx] - r["mid"]) / r["mid"]
            if side == "SHORT":
                gross = -gross
            cost = half_spread(r.get("spread", 0), r["mid"]) + half_spread(0, gm[idx]) + 2 * FEE
            rets[hz_name] = {"gross": gross, "net": gross - cost, "win": gross > 0}
        trades.append({"av": av, "side": side, "rets": rets})

    absvals = sorted(t["av"] for t in trades)

    def pct(p):
        return absvals[min(len(absvals) - 1, int(p * len(absvals)))]

    buckets = [
        ("0-50%", 0, pct(0.50)),
        ("50-75%", pct(0.50), pct(0.75)),
        ("75-90%", pct(0.75), pct(0.90)),
        ("90-99%", pct(0.90), pct(0.99)),
        ("99-100%", pct(0.99), 999),
    ]

    print("trades = %d  |tofi| p50=%.3f p75=%.3f p90=%.3f p99=%.3f"
          % (len(trades), pct(0.50), pct(0.75), pct(0.90), pct(0.99)))
    print()

    for hz in ("1s", "5s", "10s"):
        print("===== TOFI by |tofi| quantile — %s horizon =====" % hz)
        print("%-9s %5s  %-22s  %-22s" % ("bucket", "n", "LONG", "SHORT"))
        print("%-9s %5s  %6s %5s %7s %7s  %6s %5s %7s %7s" % (
            "", "", "n", "win%", "gross", "net", "n", "win%", "gross", "net"))
        print("-" * 80)
        for lo_name, lo, hi in buckets:
            sub = [t for t in trades if lo <= t["av"] < hi]
            longs = [t for t in sub if t["side"] == "LONG"]
            shorts = [t for t in sub if t["side"] == "SHORT"]
            ln = len(longs)
            sn = len(shorts)
            lw = sum(1 for t in longs if t["rets"][hz]["win"]) / ln if ln else 0
            lg = sum(t["rets"][hz]["gross"] for t in longs) / ln if ln else 0
            lnet = sum(t["rets"][hz]["net"] for t in longs) / ln if ln else 0
            sw = sum(1 for t in shorts if t["rets"][hz]["win"]) / sn if sn else 0
            sg = sum(t["rets"][hz]["gross"] for t in shorts) / sn if sn else 0
            snet = sum(t["rets"][hz]["net"] for t in shorts) / sn if sn else 0
            print("%-9s %5d  %6d %5.1f%% %+7.4f %+7.4f  %6d %5.1f%% %+7.4f %+7.4f" % (
                lo_name, ln + sn, ln, lw * 100, lg, lnet, sn, sw * 100, sg, snet))
        print()


if __name__ == "__main__":
    main()
