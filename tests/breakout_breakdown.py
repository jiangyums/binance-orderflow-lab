import csv
import sys

CSV = sys.argv[1] if len(sys.argv) > 1 else "data/features_tm.csv"


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        return [(float(r["buy_breakout"]), float(r["sell_breakout"])) for r in rd]


def windows(pairs):
    # collapse consecutive identical (buy,sell) pairs -> one window each
    out = []
    cur = None
    for p in pairs:
        if p != cur:
            out.append(p)
            cur = p
    return out


def main():
    pairs = load(CSV)
    wins = windows(pairs)
    n = len(wins)
    eps = 0.01

    def cls_b(x):
        if x == 0.0:
            return "zero"
        if x < eps:
            return "tiny"
        return "real"

    def cls_s(x):
        if x == 0.0:
            return "zero"
        if x < eps:
            return "tiny"
        return "real"

    b = [cls_b(x[0]) for x in wins]
    s = [cls_s(x[1]) for x in wins]

    def cnt(lst, v):
        return lst.count(v)

    lines = []
    lines.append("windows (100ms each): %d" % n)
    lines.append("")
    lines.append("=== buy side breakout classification ===")
    lines.append("  zero (0 buy trades) : %5d  %.1f%%" % (cnt(b, "zero"), 100*cnt(b,"zero")/n))
    lines.append("  tiny (<%.2f)         : %5d  %.1f%%" % (eps, cnt(b, "tiny"), 100*cnt(b,"tiny")/n))
    lines.append("  real (>=%.2f)        : %5d  %.1f%%" % (eps, cnt(b, "real"), 100*cnt(b,"real")/n))
    lines.append("")
    lines.append("=== sell side breakout classification ===")
    lines.append("  zero (0 sell trades): %5d  %.1f%%" % (cnt(s, "zero"), 100*cnt(s,"zero")/n))
    lines.append("  tiny (<%.2f)         : %5d  %.1f%%" % (eps, cnt(s, "tiny"), 100*cnt(s,"tiny")/n))
    lines.append("  real (>=%.2f)        : %5d  %.1f%%" % (eps, cnt(s, "real"), 100*cnt(s,"real")/n))
    lines.append("")
    lines.append("=== cross: when one side is zero, is the OTHER side active? ===")
    both_zero = sum(1 for x in wins if x[0] == 0.0 and x[1] == 0.0)
    buy_zero = cnt(b, "zero")
    sell_zero = cnt(s, "zero")
    buy_zero_sell_active = sum(1 for x in wins if x[0] == 0.0 and x[1] >= eps)
    sell_zero_buy_active = sum(1 for x in wins if x[1] == 0.0 and x[0] >= eps)
    lines.append("  both sides zero      : %5d  %.1f%%" % (both_zero, 100*both_zero/n))
    lines.append("  buy=0 & sell real    : %5d  (of buy=0: %.1f%%)" % (
        buy_zero_sell_active, 100*buy_zero_sell_active/buy_zero if buy_zero else 0))
    lines.append("  sell=0 & buy real    : %5d  (of sell=0: %.1f%%)" % (
        sell_zero_buy_active, 100*sell_zero_buy_active/sell_zero if sell_zero else 0))
    lines.append("")
    lines.append("=> buy=0 windows where SELL was active: %d / %d" % (
        buy_zero_sell_active, buy_zero))
    lines.append("=> sell=0 windows where BUY was active: %d / %d" % (
        sell_zero_buy_active, sell_zero))

    text = "\n".join(lines)
    print(text)
    with open("data/breakout_breakdown.txt", "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
