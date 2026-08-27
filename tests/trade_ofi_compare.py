import argparse
import bisect
import csv
import os
import sys

from threshold_sweep import replay_and_evaluate, aggregate


def load_rows(path):
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            feat = {}
            for k, v in row.items():
                if k == "timestamp":
                    feat[k] = int(v)
                else:
                    try:
                        feat[k] = float(v)
                    except (ValueError, TypeError):
                        feat[k] = v
            rows.append(feat)
    return rows


def compute_ofi_trade(rows):
    """Trade-based OFI = per-step change in cumulative volume delta.

    cvd already accumulates signed taker volume (BUY +qty, SELL -qty) on every
    trade event, so diff(cvd) is the true per-step aggressor flow with no
    undercounting. Depth rows (no new trade) yield 0.
    """
    out = []
    prev = None
    for r in rows:
        cur = r.get("cvd", 0.0)
        if prev is None:
            out.append(0.0)
        else:
            out.append(cur - prev)
        prev = cur
    return out


def rank_scale(vals):
    """Signed percentile rank in [-100, 100]; passes the |ofi|>1 emit gate."""
    abs_vals = [abs(v) for v in vals]
    s = sorted(abs_vals)
    n = len(s)
    out = []
    for v, a in zip(vals, abs_vals):
        if v == 0 or n == 0:
            out.append(0.0)
            continue
        r = bisect.bisect_right(s, a) / n
        out.append(r * 100.0 * (1.0 if v > 0 else -1.0))
    return out


def write_temp(rows, ofi_list, path):
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as out:
        w = csv.DictWriter(out, fieldnames=fieldnames)
        w.writeheader()
        for r, o in zip(rows, ofi_list):
            rr = dict(r)
            rr["ofi"] = o
            w.writerow(rr)


def evaluate(rows, ofi_list, thresholds, fee, obi_w, ofi_w, top_pcts, tmp_dir):
    tmp = os.path.join(tmp_dir, "cmp.csv")
    write_temp(rows, ofi_list, tmp)
    results = {}
    for thr in thresholds:
        net5_by_top = {}
        for tp in top_pcts:
            t2 = os.path.join(tmp_dir, "T%s.csv" % thr)
            replay_and_evaluate(
                tmp, thr, t2, fee, obi_w, ofi_w,
                ofi_scale=100.0, ofi_mode="linear", ofi_rank_fn=None,
                ofi_top_pct=tp,
            )
            n, (_, _), (_, a5), (_, _) = aggregate(t2)
            net5_by_top[tp] = (n, a5)
            os.remove(t2)
            print("   ... evaluated thr=%.1f top=%.0f n=%d net5=%.5f"
                  % (thr, tp, n, a5), flush=True)
        results[thr] = net5_by_top
    os.remove(tmp)
    return results


def main():
    ap = argparse.ArgumentParser(
        description="Compare book-OFI vs trade-OFI (diff of cvd) on fixed datasets."
    )
    ap.add_argument("--in-csv", required=True)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--fee", type=float, default=0.0001)
    ap.add_argument("--obi-weight", type=float, default=0.2)
    ap.add_argument("--ofi-weight", type=float, default=0.8)
    ap.add_argument("--thresholds", type=float, nargs="*", default=[0.6, 0.8])
    ap.add_argument("--top-pct", type=float, nargs="*", default=[0.0, 2.0])
    args = ap.parse_args()

    tmp_dir = "data/_cmp_tmp"
    os.makedirs(tmp_dir, exist_ok=True)

    in_rows = load_rows(args.in_csv)
    out_rows = load_rows(args.out_csv)

    in_book = [r["ofi"] for r in in_rows]
    out_book = [r["ofi"] for r in out_rows]
    in_trade = compute_ofi_trade(in_rows)
    out_trade = compute_ofi_trade(out_rows)

    in_book_r = rank_scale(in_book)
    out_book_r = rank_scale(out_book)
    in_trade_r = rank_scale(in_trade)
    out_trade_r = rank_scale(out_trade)

    print("book-OFI vs trade-OFI  (fee=%.4f, obi_w=%.2f, ofi_w=%.2f)\n"
          % (args.fee, args.obi_weight, args.ofi_weight), flush=True)
    print("dataset | source | thr | top%% |  n  |  net5", flush=True)
    print("-" * 52, flush=True)

    for label, rows, book_r, trade_r in (
        ("IN ", in_rows, in_book_r, in_trade_r),
        ("OUT", out_rows, out_book_r, out_trade_r),
    ):
        book_res = evaluate(rows, book_r, args.thresholds, args.fee,
                            args.obi_weight, args.ofi_weight, args.top_pct, tmp_dir)
        trade_res = evaluate(rows, trade_r, args.thresholds, args.fee,
                             args.obi_weight, args.ofi_weight, args.top_pct, tmp_dir)
        for thr in args.thresholds:
            for tp in args.top_pct:
                bn, ba = book_res[thr][tp]
                tn, ta = trade_res[thr][tp]
                print("%s   | %6s | %.1f | %3.0f | %4d | %.5f"
                      % (label, "book", thr, tp, bn, ba))
                print("%s   | %6s | %.1f | %3.0f | %4d | %.5f"
                      % ("   ", "trade", thr, tp, tn, ta))

    print("\ntrade-OFI = diff(cvd); both sources rank-normalized to [-100,100].")


if __name__ == "__main__":
    main()
