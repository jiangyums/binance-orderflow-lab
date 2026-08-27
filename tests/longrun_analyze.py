import csv
import sys

MAIN = sys.argv[1] if len(sys.argv) > 1 else None
BINS = sys.argv[2] if len(sys.argv) > 2 else None

MIN_N = 50

BIN_LB = {
    "0-0.01": 0.0,
    "0.01-0.1": 0.01,
    "0.1-0.5": 0.1,
    "0.5-1": 0.5,
    "1-5": 1.0,
    "5+": 5.0,
}


def load(path):
    if path is None:
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def horizons_from(cols):
    hs = []
    for c in cols:
        if c.startswith("ofi_hit_") and c.endswith("s"):
            hs.append(int(c[len("ofi_hit_"):-1]))
    return sorted(hs)


def main():
    if MAIN is None or BINS is None:
        import glob
        ms = sorted(f for f in glob.glob("data/monitor_*.csv") if "bins" not in f)
        bs = sorted(glob.glob("data/*_bins_*.csv"))
        MAIN_ = ms[-1] if ms else None
        BINS_ = bs[-1] if bs else None
    else:
        MAIN_ = MAIN
        BINS_ = BINS

    out = []
    out.append("=== long-run analysis (multi-horizon) ===")
    out.append("main : %s" % MAIN_)
    out.append("bins : %s" % BINS_)
    out.append("(bins with n<%d flagged '*' = not yet reliable)" % MIN_N)
    out.append("")

    main_rows = load(MAIN_)
    bin_rows = load(BINS_)
    hs = horizons_from(main_rows[0].keys()) if main_rows else [1, 5, 10, 30]
    out.append("horizons (s): %s" % hs)
    out.append("")

    # ---- Q1: per-hour book-OFI vs trade-OFI hit rate, per horizon ----
    hourly = {}
    for r in main_rows:
        ts = fnum(r["ts_bucket"])
        hr = int(ts // (3600 * 1000))
        h = hourly.setdefault(hr, {"n": 0.0})
        n = fnum(r["n"])
        h["n"] += n
        for hz in hs:
            ov = fnum(r["ofi_hit_%ds" % hz])
            tv = fnum(r["tofi_hit_%ds" % hz])
            kw = "o%d_w" % hz
            h.setdefault(kw, 0.0)
            h.setdefault(kw + "n", 0.0)
            if ov == ov:
                h[kw] += ov * n
                h[kw + "n"] += n
            kt = "t%d_w" % hz
            h.setdefault(kt, 0.0)
            h.setdefault(kt + "n", 0.0)
            if tv == tv:
                h[kt] += tv * n
                h[kt + "n"] += n
            for key, wkey in (("comp05_hit_%ds" % hz, "c05%d" % hz),
                              ("comp1_hit_%ds" % hz, "c1%d" % hz)):
                cv = fnum(r.get(key, ""))
                if cv == cv:
                    wk = wkey + "_w"
                    wn = wkey + "_wn"
                    h[wk] = h.get(wk, 0.0) + cv * n
                    h[wn] = h.get(wn, 0.0) + n

    out.append("--- Q1: per-hour hit rate (book-OFI / trade-OFI) by horizon ---")
    hdr = "%-8s %8s" % ("hour", "n")
    for hz in hs:
        hdr += "  ofi_%ds  tofi_%ds" % (hz, hz)
    out.append(hdr)
    for hr in sorted(hourly):
        h = hourly[hr]
        line = "%-8d %8d" % (hr, int(h["n"]))
        for hz in hs:
            oh = h["o%d_w" % hz] / h["o%d_wn" % hz] if h["o%d_wn" % hz] else float("nan")
            th = h["t%d_w" % hz] / h["t%d_wn" % hz] if h["t%d_wn" % hz] else float("nan")
            line += "  %6.3f  %6.3f" % (oh, th)
        out.append(line)
    out.append("")

    # ---- Q1b: per-hour COMPOSITE (regime-weighted) hit rate ----
    comphs = [hz for hz in hs
              if ("comp05_hit_%ds" % hz) in (main_rows[0].keys() if main_rows else [])]
    if comphs:
        out.append("--- Q1b: per-hour COMPOSITE hit (quiet->trade-OFI, extreme->book-OFI) ---")
        out.append("      (c05 = switch at breakout>=0.5, c1 = switch at breakout>=1.0)")
        hdr = "%-8s %8s" % ("hour", "n")
        for hz in comphs:
            hdr += "  c05_%ds  c1_%ds" % (hz, hz)
        out.append(hdr)
        for hr in sorted(hourly):
            h = hourly[hr]
            line = "%-8d %8d" % (hr, int(h["n"]))
            for hz in comphs:
                c5 = h["c05%d_w" % hz] / h["c05%d_wn" % hz] if h.get("c05%d_wn" % hz) else float("nan")
                c1 = h["c1%d_w" % hz] / h["c1%d_wn" % hz] if h.get("c1%d_wn" % hz) else float("nan")
                line += "  %6.3f  %6.3f" % (c5, c1)
            out.append(line)
        out.append("")

    # ---- Q1c: composite lift over PURE trade-OFI, per horizon ----
    if comphs:
        out.append("--- Q1c: composite lift over PURE trade-OFI (pp, pooled across hours) ---")
        out.append("  horizon    tofi      c05       c1     c05-tofi   c1-tofi")
        for hz in comphs:
            tw = 0.0
            tn = 0.0
            c5w = 0.0
            c5n = 0.0
            c1w = 0.0
            c1n = 0.0
            for hr in sorted(hourly):
                h = hourly[hr]
                if h.get("t%d_wn" % hz):
                    tw += h["t%d_w" % hz]
                    tn += h["t%d_wn" % hz]
                if h.get("c05%d_wn" % hz):
                    c5w += h["c05%d_w" % hz]
                    c5n += h["c05%d_wn" % hz]
                if h.get("c1%d_wn" % hz):
                    c1w += h["c1%d_w" % hz]
                    c1n += h["c1%d_wn" % hz]
            tofi = tw / tn if tn else float("nan")
            c05 = c5w / c5n if c5n else float("nan")
            c1 = c1w / c1n if c1n else float("nan")
            d5 = (c05 - tofi) * 100 if (c5n and tn) else float("nan")
            d1 = (c1 - tofi) * 100 if (c1n and tn) else float("nan")
            out.append("  %5ds  %7.3f  %7.3f  %7.3f  %+8.2f   %+8.2f" %
                       (hz, tofi, c05, c1, d5, d1))
        out.append("")

    # ---- Q2 + Q3: by breakout bin, per horizon; regime rollup ----
    agg = {}
    regimes = {hz: {"quiet": _z(), "mid": _z(), "ext1": _z(), "ext05": _z()}
               for hz in hs}
    for r in bin_rows:
        lab = r["bin"]
        n = int(fnum(r["n"]))
        lb = BIN_LB.get(lab, -1.0)
        targets = []
        if lb == 0:
            targets.append("quiet")
        if 0 < lb < 1:
            targets.append("mid")
        if lb >= 0.5:
            targets.append("ext05")
        if lb >= 1:
            targets.append("ext1")
        a = agg.setdefault(lab, {hz: {"ofi_h": 0.0, "ofi_n": 0.0,
                                     "tofi_h": 0.0, "tofi_n": 0.0,
                                     "agree_h": 0.0, "agree_n": 0.0,
                                     "n_total": 0.0}
                                for hz in hs})
        for hz in hs:
            b = a[hz]
            b["n_total"] += n
            rate = fnum(r["ofi_hit_%ds" % hz])
            rate2 = fnum(r["tofi_hit_%ds" % hz])
            rate3 = fnum(r["agree_%ds" % hz])
            if rate == rate:
                b["ofi_h"] += rate * n
                b["ofi_n"] += n
            if rate2 == rate2:
                b["tofi_h"] += rate2 * n
                b["tofi_n"] += n
            if rate3 == rate3:
                b["agree_h"] += rate3 * n
                b["agree_n"] += n
            for t in targets:
                z = regimes[hz][t]
                if rate == rate:
                    z["ofi_h"] += rate * n
                    z["ofi_n"] += n
                if rate2 == rate2:
                    z["tofi_h"] += rate2 * n
                    z["tofi_n"] += n
                if rate3 == rate3:
                    z["agree_h"] += rate3 * n
                    z["agree_n"] += n

    for hz in hs:
        out.append("--- Q2 (%ds): by breakout bin ---" % hz)
        out.append("    bin    n     ofi_hit  tofi_hit   agree(ofi~tofi)")
        for lab in ["0-0.01", "0.01-0.1", "0.1-0.5", "0.5-1", "1-5", "5+"]:
            if lab not in agg:
                continue
            a = agg[lab][hz]
            oh = a["ofi_h"] / a["ofi_n"] if a["ofi_n"] else float("nan")
            th = a["tofi_h"] / a["tofi_n"] if a["tofi_n"] else float("nan")
            ag = a["agree_h"] / a["agree_n"] if a["agree_n"] else float("nan")
            flag = " *" if a["n_total"] < MIN_N else ""
            out.append("  %-8s %7d  %8.3f  %8.3f  %14.3f%s" % (lab, int(a["n_total"]), oh, th, ag, flag))
        out.append("")

    out.append("--- Q3: REGIME rollup (answers 'does taker>>wall break the signal?') ---")
    out.append("    regime              n    ofi_hit  tofi_hit   agree")
    for hz in hs:
        rg = regimes[hz]
        for name, lab in [("quiet (breakout~0)", "quiet"),
                         ("mid (0<bo<1)", "mid"),
                         ("extreme (bo>=0.5)", "ext05"),
                         ("extreme (bo>=1)", "ext1")]:
            z = rg[lab]
            if z["ofi_n"] == 0:
                continue
            oh = z["ofi_h"] / z["ofi_n"]
            th = z["tofi_h"] / z["tofi_n"]
            ag = z["agree_h"] / z["agree_n"] if z["agree_n"] else float("nan")
            nd = int(z["ofi_n"] / len(hs))
            flag = " *" if nd < MIN_N else ""
            out.append("  %-20s %7d  %8.3f  %8.3f  %8.3f%s" % (name, nd, oh, th, ag, flag))
        out.append("")

    out.append("read:")
    out.append("  ofi_hit/tofi_hit = sign(signal @T)==sign(fwd_ret over H s) rate")
    out.append("  agree = book-OFI & trade-OFI same direction")
    out.append("  Q1b = composite hit (quiet->trade-OFI, extreme->book-OFI)")
    out.append("  Q1c = composite lift over PURE trade-OFI, in percentage points, per horizon")
    out.append("  if extreme(bo>=1) hit ~ quiet hit  -> signal holds even when taker>>wall")
    out.append("  if extreme(bo>=1) hit drops a lot  -> taker>>wall DOES break the signal")
    out.append("  '*' = n<%d, ignore until enough samples accumulate" % MIN_N)

    text = "\n".join(out)
    print(text)
    with open("data/longrun_analysis.txt", "w", encoding="utf-8") as f:
        f.write(text)


def _z():
    return {"ofi_h": 0.0, "ofi_n": 0.0, "tofi_h": 0.0, "tofi_n": 0.0,
            "agree_h": 0.0, "agree_n": 0.0}


if __name__ == "__main__":
    main()
