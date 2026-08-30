import csv
import sys

csv.field_size_limit(2_147_483_647)

sys.path.insert(0, ".")

from src.orderflow.validator.stream_validator import StreamValidator


def load(path):

    rows = []

    with open(path, encoding="utf-8", newline="") as f:

        for row in csv.DictReader(f):

            try:

                ts = int(row["timestamp"])

            except (ValueError, TypeError, KeyError):

                continue

            try:

                tofi = float(row.get("tofi", "0"))

            except (ValueError, TypeError):

                tofi = 0.0

            rows.append((ts, tofi))

    rows.sort(key=lambda x: x[0])

    return rows


def main():

    path = sys.argv[1] if len(sys.argv) > 1 else "data/features.csv"

    gap_warn_ms = int(sys.argv[2]) if len(sys.argv) > 2 else 3000

    rows = load(path)

    print("source:", path, " rows =", len(rows))

    v_depth = StreamValidator(gap_warn_ms=gap_warn_ms, report_every=10**9)
    v_trade = StreamValidator(gap_warn_ms=gap_warn_ms, report_every=10**9)

    for ts, tofi in rows:

        if tofi == 0.0:

            v_depth.check("depth", ts)

        else:

            v_trade.check("trade", ts)

    print("\n===== interval report (sorted by timestamp) =====")

    for name, v in (("depth (tofi==0)", v_depth), ("trade (tofi!=0)", v_trade)):

        s = v._stats["depth" if "depth" in name else "trade"]

        n = s["count"]

        if n == 0:

            print("%s: no data" % name)

            continue

        samples = sorted(s["samples"])

        m = len(samples)

        p = lambda q: samples[min(m - 1, int(q * m))]

        print("%s: n=%d mean=%.1fms p50=%d p90=%d p99=%d min=%d max=%d"
              % (name, n, s["total"] / n, p(0.5), p(0.9), p(0.99),
                 s["min"] or 0, s["max"]))


if __name__ == "__main__":

    main()
