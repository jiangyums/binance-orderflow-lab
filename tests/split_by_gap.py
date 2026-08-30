import csv
import sys

csv.field_size_limit(2_147_483_647)

sys.path.insert(0, ".")

SRC = "data/_snapshot_features.csv"
BEFORE = "data/features_before_gap.csv"
AFTER = "data/features_after_gap.csv"


def load(path):

    with open(path, encoding="utf-8", newline="") as f:

        r = csv.DictReader(f)

        cols = r.fieldnames

        rows = []

        for row in r:

            try:

                row["timestamp"] = int(row["timestamp"])

            except (ValueError, TypeError, KeyError):

                continue

            try:

                row["tofi"] = float(row.get("tofi", "0"))

            except (ValueError, TypeError):

                row["tofi"] = 0.0

            rows.append(row)

    rows.sort(key=lambda x: x["timestamp"])

    return cols, rows


def find_gap(rows, min_gap_ms=60000):

    prev = None

    best = None

    for r in rows:

        if r["tofi"] != 0.0:

            if prev is not None:

                gap = r["timestamp"] - prev

                if gap > min_gap_ms and (best is None or gap > best[0]):

                    best = (gap, prev, r["timestamp"])

            prev = r["timestamp"]

    return best


def main():

    cols, rows = load(SRC)

    gap = find_gap(rows)

    if gap is None:

        print("no gap found, abort")

        return

    gap_ms, gap_start, gap_end = gap

    print("largest trade gap: %.1fs (%d -> %d)" % (gap_ms / 1000, gap_start, gap_end))

    before = [r for r in rows if r["timestamp"] <= gap_start]

    after = [r for r in rows if r["timestamp"] >= gap_end]

    def write(path, subset):

        with open(path, "w", encoding="utf-8", newline="") as f:

            w = csv.DictWriter(f, fieldnames=cols)

            w.writeheader()

            for r in subset:

                w.writerow({c: r[c] for c in cols})

    write(BEFORE, before)

    write(AFTER, after)

    print("before: %d rows -> %s" % (len(before), BEFORE))

    print("after:  %d rows -> %s" % (len(after), AFTER))

    print("dropped gap-zone rows: %d" % (len(rows) - len(before) - len(after)))


if __name__ == "__main__":

    main()
