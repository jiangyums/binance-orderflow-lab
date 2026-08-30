import csv
import sys

csv.field_size_limit(2_147_483_647)

sys.path.insert(0, ".")

SRC = "data/features_v2.csv"
OUT_PREFIX = "data/features_v2_seg"
GAP_MIN_MS = 60000          # 超过60s的空洞才切分


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


def main():

    cols, rows = load(SRC)

    # 找 trade 空洞
    prev = None

    gaps = []          # (prev_ts, next_ts)

    boundaries = []    # 切分点（下一段起点 ts）

    for r in rows:

        if r["tofi"] != 0.0:

            if prev is not None:

                gap = r["timestamp"] - prev

                if gap > GAP_MIN_MS:

                    gaps.append((prev, r["timestamp"]))

                    boundaries.append(r["timestamp"])

            prev = r["timestamp"]

    # 切分
    segs = []

    start = 0

    for b in boundaries:

        seg = [r for r in rows if start <= r["timestamp"] < b]

        if seg:

            segs.append(seg)

        start = b

    last_seg = [r for r in rows if r["timestamp"] >= start]

    if last_seg:

        segs.append(last_seg)

    print("total rows: %d" % len(rows))

    print("gaps found: %d" % len(gaps))

    for i, (a, b) in enumerate(gaps):

        print("  gap %d: %.1fs" % (i + 1, (b - a) / 1000.0))

    print("\nsegments: %d" % len(segs))

    for i, seg in enumerate(segs):

        span = (seg[-1]["timestamp"] - seg[0]["timestamp"]) / 60000.0

        n_tr = sum(1 for r in seg if r["tofi"] != 0.0)

        n_dep = len(seg) - n_tr

        print("  seg%d: rows=%d trade=%d depth=%d span=%.1fmin"
              % (i, len(seg), n_tr, n_dep, span))

    # 写文件
    for i, seg in enumerate(segs):

        path = "%s_%d.csv" % (OUT_PREFIX, i)

        with open(path, "w", encoding="utf-8", newline="") as f:

            w = csv.DictWriter(f, fieldnames=cols)

            w.writeheader()

            for r in seg:

                w.writerow({c: r[c] for c in cols})

        print("  wrote %s" % path)


if __name__ == "__main__":

    main()
