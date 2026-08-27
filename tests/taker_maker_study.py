import csv
import os
import sys

CSV = sys.argv[1] if len(sys.argv) > 1 else "data/features_tm.csv"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/taker_maker_study.txt"
FWD = 10  # ~1s forward return proxy (rows)


def sgn(x):
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def hit_rate(a, b):
    sa, sb, n = [], [], 0
    hit = 0
    for x, y in zip(a, b):
        sx, sy = sgn(x), sgn(y)
        if sx == 0 or sy == 0:
            continue
        n += 1
        if sx == sy:
            hit += 1
    return (hit / n) if n else float("nan")


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        rows = list(rd)
    cols = {}
    for k in ["timestamp", "mid", "cvd", "ofi", "buy_breakout",
              "sell_breakout", "bid_depth", "ask_depth"]:
        cols[k] = [float(r.get(k, "nan")) if r.get(k) not in (None, "") else float("nan")
                   for r in rows]
    n = len(rows)
    cvd = cols["cvd"]
    tofi = [float("nan")] * n
    for i in range(1, n):
        tofi[i] = cvd[i] - cvd[i - 1]
    cols["trade_ofi"] = tofi
    return cols, rows


def bucket_stats(cols, col, idxs):
    sub = idxs
    tofi = [cols["trade_ofi"][i] for i in sub]
    bofi = [cols["ofi"][i] for i in sub]
    fwd = [cols["fwd_ret"][i] for i in sub]
    thr = [cols[col][i] for i in sub]
    # sign disagreement book vs trade
    dis = 0
    dn = 0
    for x, y in zip(bofi, tofi):
        sx, sy = sgn(x), sgn(y)
        if sx == 0 or sy == 0:
            continue
        dn += 1
        if sx != sy:
            dis += 1
    return {
        "n": len(sub),
        "mean_col": sum(thr) / len(thr) if thr else float("nan"),
        "mean_tofi": sum(tofi) / len(tofi) if tofi else float("nan"),
        "mean_bofi": sum(bofi) / len(bofi) if bofi else float("nan"),
        "fwd_bps": (sum(fwd) / len(fwd) * 1e4) if fwd else float("nan"),
        "t_hit": hit_rate(tofi, fwd),
        "b_hit": hit_rate(bofi, fwd),
        "disagree": (dis / dn) if dn else float("nan"),
    }


def quintiles(cols, col):
    n = len(cols["timestamp"])
    order = sorted(range(n), key=lambda i: cols[col][i])
    size = n // 5
    edges = [order[i * size:(i + 1) * size] for i in range(5)]
    if len(edges[4]) < size:  # last bin may be larger
        edges[4] = order[4 * size:]
    return edges


def main():
    cols, rows = load(CSV)
    n = len(cols["timestamp"])
    cols["fwd_ret"] = [float("nan")] * n
    for i in range(n - FWD):
        if cols["mid"][i] != 0:
            cols["fwd_ret"][i] = cols["mid"][i + FWD] / cols["mid"][i] - 1

    out = []
    out.append("=== Taker-Maker breakout study ===")
    out.append("file: %s  rows: %d" % (CSV, n))
    out.append("trade_ofi = diff(cvd) | fwd_ret = mid.shift(-%d)/mid-1" % FWD)
    out.append("hit = sign(signal)==sign(fwd_ret) | disagree = sign(book)!=sign(trade)")
    out.append("")
    ot = hit_rate(cols["trade_ofi"], cols["fwd_ret"])
    ob = hit_rate(cols["ofi"], cols["fwd_ret"])
    out.append("OVERALL hit  trade-OFI(diff cvd)=%.3f  book-OFI(ofi)=%.3f" % (ot, ob))
    out.append("")

    for col in ["buy_breakout", "sell_breakout"]:
        out.append("--- by %s quintile ---" % col)
        out.append("%-4s %7s %12s %12s %12s %10s %8s %8s %9s" % (
            "bin", "n", "mean_" + col[:4], "mean_tOFI", "mean_bOFI",
            "fwd_bps", "t_hit", "b_hit", "disagree"))
        bins = quintiles(cols, col)
        for b, idxs in enumerate(bins):
            if not idxs:
                continue
            s = bucket_stats(cols, col, idxs)
            out.append("%-4d %7d %12.4f %12.5f %12.5f %10.2f %8.3f %8.3f %9.3f" % (
                b, s["n"], s["mean_col"], s["mean_tofi"], s["mean_bofi"],
                s["fwd_bps"], s["t_hit"], s["b_hit"], s["disagree"]))
        out.append("")

    text = "\n".join(out)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)

    # Conditional: among rows where book-OFI is decisive (nonzero), does the
    # same-side breakout change book-OFI reliability? (the "does breakout fix
    # OFI failure" test). High breakout = wall pierced; low = wall absorbed.
    cond = []
    cond.append("")
    cond.append("=== conditional: book-OFI reliability by same-side breakout ===")
    cond.append("subset: book-OFI != 0 ; breakout_side = buy if bOFI>0 else sell")
    cond.append("%-10s %7s %10s %9s %9s" % ("breakout", "n", "bOFI_hit", "tOFI_hit", "fwd_bps"))
    for lo, hi, label in [(0.0, 0.0, "==0"), (0.0, 1e9, ">0")]:
        sub_idx = []
        for i in range(n):
            b = cols["ofi"][i]
            if sgn(b) == 0:
                continue
            bc = cols["buy_breakout"][i] if b > 0 else cols["sell_breakout"][i]
            if lo == 0.0 and hi == 0.0:
                if bc == 0.0:
                    sub_idx.append(i)
            else:
                if bc > 0.0:
                    sub_idx.append(i)
        if not sub_idx:
            continue
        bofi = [cols["ofi"][i] for i in sub_idx]
        tofi = [cols["trade_ofi"][i] for i in sub_idx]
        fwd = [cols["fwd_ret"][i] for i in sub_idx]
        cond.append("%-10s %7d %10.3f %9.3f %9.2f" % (
            label, len(sub_idx), hit_rate(bofi, fwd), hit_rate(tofi, fwd),
            sum(fwd) / len(fwd) * 1e4))
    ctext = "\n".join(cond)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(ctext)
    print(ctext)


if __name__ == "__main__":
    main()
