import csv
import bisect

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
    # Depth/trade websockets arrive out of order; bisect-based return lookup
    # requires an ascending timeline, so sort by timestamp first.
    rows.sort(key=lambda x: x["timestamp"])
    return rows


def evaluate(rows, signal_fn):
    timestamps = [r["timestamp"] for r in rows]
    mids = [r["mid"] for r in rows]
    spreads = [r.get("spread", 0.0) for r in rows]

    last = None
    signals = []  # (t0, side, entry, spread)
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


def make_trade_ofi(t):
    def f(r):
        tofi = r["tofi"]
        if tofi > t:
            return "LONG"
        if tofi < -t:
            return "SHORT"
        return "FLAT"
    return f


def make_book_ofi(t):
    def f(r):
        ofi = r["ofi"]
        if ofi > t:
            return "LONG"
        if ofi < -t:
            return "SHORT"
        return "FLAT"
    return f


def make_agree(tofi_floor):
    # Emit only when book-OFI and trade-OFI agree on direction.
    def f(r):
        tofi = r["tofi"]
        ofi = r["ofi"]
        if abs(tofi) < tofi_floor:
            return "FLAT"
        if ofi == 0:
            return "FLAT"
        if tofi > 0 and ofi > 0:
            return "LONG"
        if tofi < 0 and ofi < 0:
            return "SHORT"
        return "FLAT"
    return f


def make_regime(bo_t, tofi_floor, ofi_floor):
    # Extreme breakout -> book-OFI driver; otherwise trade-OFI driver.
    def f(r):
        nb = abs(r["buy_breakout"] - r["sell_breakout"])
        tofi = r["tofi"]
        ofi = r["ofi"]
        if nb >= bo_t:
            if abs(ofi) < ofi_floor:
                return "FLAT"
            return "LONG" if ofi > 0 else "SHORT"
        else:
            if abs(tofi) < tofi_floor:
                return "FLAT"
            return "LONG" if tofi > 0 else "SHORT"
    return f


def main():
    rows = load("data/features.csv")
    print("rows (sorted) =", len(rows))
    print()
    print(
        "%-34s %6s %6s %6s | %7s %7s %7s | %8s %8s %8s"
        % (
            "scheme",
            "n1", "n5", "n10",
            "win1%", "win5%", "win10%",
            "net1", "net5", "net10",
        )
    )
    print("-" * 96)

    schemes = []
    for t in [0.0, 0.002, 0.01, 0.05, 0.1, 0.5, 1.0]:
        schemes.append(("trade_ofi t=%.3f" % t, make_trade_ofi(t)))
    for t in [0.0, 0.1, 0.5, 1.0, 5.0, 10.0, 20.0]:
        schemes.append(("book_ofi t=%.2f" % t, make_book_ofi(t)))
    for t in [0.0, 0.002, 0.01, 0.05]:
        schemes.append(("agree tofi_floor=%.3f" % t, make_agree(t)))
    for bo in [0.05, 0.1, 0.5]:
        schemes.append(
            ("regime bo>=%.2f (floors .002/.1)" % bo, make_regime(bo, 0.002, 0.1))
        )

    for name, fn in schemes:
        o = evaluate(rows, fn)
        print(
            "%-34s %6d %6d %6d | %6.1f%% %6.1f%% %6.1f%% | %+7.5f %+7.5f %+7.5f"
            % (
                name,
                o["n1"], o["n5"], o["n10"],
                o["win1"] * 100, o["win5"] * 100, o["win10"] * 100,
                o["net1"], o["net5"], o["net10"],
            )
        )


if __name__ == "__main__":
    main()
