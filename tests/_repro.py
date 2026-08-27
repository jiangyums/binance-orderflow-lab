import sys, math
sys.path.insert(0, ".")
from src.orderflow.collector.monitor import MonitorRecorder

# synthetic stream: depth every 100ms (cvd unchanged), trades every ~200ms (cvd steps)
rec = MonitorRecorder(prefix="data/_repro", bucket=60, horizons=(1, 5, 10, 30))

t = 1_787_000_000_000  # ms
cvd = 1000.0
import random
random.seed(0)
for i in range(20000):  # ~20000*100ms = 2000s ~ 33 min
    t += 100
    # depth event (cvd constant)
    feat = {
        "timestamp": t,
        "mid": 100 + 0.01 * math.sin(i / 50.0),
        "ofi": random.uniform(-2, 2),
        "cvd": cvd,
        "buy_breakout": random.uniform(0, 6),
        "sell_breakout": random.uniform(0, 6),
    }
    rec.write(feat)
    # trade event every 2nd tick -> cvd changes
    if i % 2 == 0:
        t += 1
        cvd += random.choice([-1, 1]) * random.uniform(0.1, 3.0)
        feat2 = {
            "timestamp": t,
            "mid": 100 + 0.01 * math.sin(i / 50.0),
            "ofi": 0.0,
            "cvd": cvd,
            "buy_breakout": random.uniform(0, 6),
            "sell_breakout": random.uniform(0, 6),
        }
        rec.write(feat2)
rec.close()

import csv
with open(rec.main_path, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
unique = set(r["ts_bucket"] for r in rows)
print("rows=%d unique_ts_bucket=%d" % (len(rows), len(unique)))
print("expected ~%d buckets (interval/60s)" % ((t - 1_787_000_000_000)//60000))
# show n distribution
from collections import Counter
c = Counter()
for r in rows:
    nn = int(r["n"])
    c["n>=1000" if nn >= 1000 else ("100<=n<1000" if nn >= 100 else "n<100")] += 1
print(dict(c))
