import asyncio
import csv
import math
import os
import time

from asyncio import Queue

from src.orderflow import market_state
from src.orderflow.collector.binance_depth import orderbook_worker
from src.orderflow.collector.binance_trade import trade_worker
from src.orderflow.engine import OrderFlowEngine


# breakout bins: [lo, hi) on max(buy_breakout, sell_breakout)
BREAKOUT_BINS = [
    (0.0, 0.01, "0-0.01"),
    (0.01, 0.1, "0.01-0.1"),
    (0.1, 0.5, "0.1-0.5"),
    (0.5, 1.0, "0.5-1"),
    (1.0, 5.0, "1-5"),
    (5.0, float("inf"), "5+"),
]


def bin_label(lvl):
    for lo, hi, lab in BREAKOUT_BINS:
        if lo <= lvl < hi:
            return lab
    return "5+"


def _pct(values, p):
    if not values:
        return float("nan")
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
    return s[k]


class BucketAcc:
    def __init__(self, ts):
        self.ts = ts
        self.n = 0
        self.ofi_sum = 0.0
        self.ofi_abs = 0.0
        self.tofi_sum = 0.0
        self.tofi_abs = 0.0
        self.ofi_hit = 0
        self.ofi_hit_n = 0
        self.tofi_hit = 0
        self.tofi_hit_n = 0
        self.agree = 0
        self.agree_n = 0
        self.comp05_hit = 0
        self.comp05_hit_n = 0
        self.comp1_hit = 0
        self.comp1_hit_n = 0
        self.bk = []
        self.sk = []
        self.bins = {
            lab: {"n": 0, "ofi_hit": 0, "ofi_hit_n": 0,
                  "tofi_hit": 0, "tofi_hit_n": 0,
                  "agree": 0, "agree_n": 0}
            for _, _, lab in BREAKOUT_BINS
        }

    def add(self, ofi, tofi, bk, sk, fwd_ret):
        self.n += 1
        self.ofi_sum += ofi
        self.ofi_abs += abs(ofi)
        self.tofi_sum += tofi
        self.tofi_abs += abs(tofi)
        self.bk.append(bk if bk == bk else 0.0)
        self.sk.append(sk if sk == sk else 0.0)

        if ofi != 0 and fwd_ret != 0:
            self.ofi_hit_n += 1
            if (ofi > 0) == (fwd_ret > 0):
                self.ofi_hit += 1
        if tofi != 0 and fwd_ret != 0:
            self.tofi_hit_n += 1
            if (tofi > 0) == (fwd_ret > 0):
                self.tofi_hit += 1
        if ofi != 0 and tofi != 0:
            self.agree_n += 1
            if (ofi > 0) == (tofi > 0):
                self.agree += 1

        # composite (regime-weighted): quiet -> trade-OFI, extreme -> book-OFI
        bo = max(bk, sk)
        for _thr, _ch, _cn in ((0.5, "comp05_hit", "comp05_hit_n"),
                               (1.0, "comp1_hit", "comp1_hit_n")):
            _d = tofi if bo < _thr else ofi
            if _d != 0 and fwd_ret != 0:
                setattr(self, _cn, getattr(self, _cn) + 1)
                if (_d > 0) == (fwd_ret > 0):
                    setattr(self, _ch, getattr(self, _ch) + 1)

        lab = bin_label(max(bk, sk))
        b = self.bins[lab]
        b["n"] += 1
        if ofi != 0 and fwd_ret != 0:
            b["ofi_hit_n"] += 1
            if (ofi > 0) == (fwd_ret > 0):
                b["ofi_hit"] += 1
        if tofi != 0 and fwd_ret != 0:
            b["tofi_hit_n"] += 1
            if (tofi > 0) == (fwd_ret > 0):
                b["tofi_hit"] += 1
        if ofi != 0 and tofi != 0:
            b["agree_n"] += 1
            if (ofi > 0) == (tofi > 0):
                b["agree"] += 1

    def hit(self, k):
        a = getattr(self, k)
        n = getattr(self, k + "_n")
        return (a / n) if n else float("nan")


class MonitorRecorder:
    """Inline aggregator: per-bucket compact summary + per-breakout-bin stats,
    computed at MULTIPLE forward horizons (1/5/10s) in a single pass.

    No giant raw file. Trade-OFI = diff(cvd); forward return at each horizon via
    a short rolling buffer. Answers (1) long-run book-OFI vs trade-OFI and
    (2) failure when taker >> maker wall, across horizons.
    """

    def __init__(self, prefix="data/monitor", bucket=60, horizons=(1, 5, 10)):
        self.bucket = bucket
        self.horizons = list(horizons)
        self.max_h = max(self.horizons)
        self.prev_cvd = None
        self.buffer = []
        self.accs = {}

        stamp = time.strftime("%Y%m%d_%H%M%S")
        self.main_path = "%s_%s.csv" % (prefix, stamp)
        self.bin_path = "%s_bins_%s.csv" % (prefix, stamp)
        d = os.path.dirname(self.main_path)
        if d:
            os.makedirs(d, exist_ok=True)
        self.f_main = open(self.main_path, "w", newline="", encoding="utf-8")
        self.f_bin = open(self.bin_path, "w", newline="", encoding="utf-8")
        self.w_main = csv.DictWriter(self.f_main, fieldnames=self.MAIN_FIELDS)
        self.w_main.writeheader()
        self.f_main.flush()
        self.w_bin = csv.DictWriter(self.f_bin, fieldnames=self.BIN_FIELDS)
        self.w_bin.writeheader()
        self.f_bin.flush()

    @property
    def MAIN_FIELDS(self):
        f = ["ts_bucket", "n"]
        for h in self.horizons:
            f += ["ofi_hit_%ds" % h, "tofi_hit_%ds" % h, "agree_%ds" % h,
                  "comp05_hit_%ds" % h, "comp1_hit_%ds" % h]
        f += ["bk_mean", "bk_p95", "bk_max", "sk_mean", "sk_p95", "sk_max"]
        return f

    @property
    def BIN_FIELDS(self):
        f = ["ts_bucket", "bin", "n"]
        for h in self.horizons:
            f += ["ofi_hit_%ds" % h, "tofi_hit_%ds" % h, "agree_%ds" % h]
        return f

    def write(self, feature):
        ts = feature.get("timestamp")
        cvd = feature.get("cvd")
        if cvd is None or self.prev_cvd is None:
            self.prev_cvd = cvd
            return
        tofi = cvd - self.prev_cvd
        self.prev_cvd = cvd

        bk = feature.get("buy_breakout") or 0.0
        sk = feature.get("sell_breakout") or 0.0
        ofi = feature.get("ofi") or 0.0
        mid = feature.get("mid")
        if mid is None:
            return

        self.buffer.append({"ts": ts, "mid": mid, "ofi": ofi,
                            "tofi": tofi, "bk": bk, "sk": sk})
        # keep buffer ordered by ts so finalize always drains the oldest
        # first even when depth/trade streams interleave slightly out of order
        self.buffer.sort(key=lambda e: e["ts"])

        # finalize records old enough for the longest horizon
        thr = ts - self.max_h * 1000
        while self.buffer and self.buffer[0]["ts"] <= thr:
            old = self.buffer.pop(0)
            fwd = {}
            for h in self.horizons:
                m = self._mid_at(old["ts"] + h * 1000)
                fwd[h] = (m / old["mid"] - 1.0) if (m and old["mid"]) else 0.0
            self._accumulate(old, fwd)
        self._flush_closed(ts)

    def _mid_at(self, target):
        best = None
        best_d = None
        for e in self.buffer:
            d = abs(e["ts"] - target)
            if best_d is None or d < best_d:
                best_d = d
                best = e
        return best["mid"] if best else None

    def _accumulate(self, rec, fwd_dict):
        bts = (rec["ts"] // (self.bucket * 1000)) * (self.bucket * 1000)
        a = self.accs.get(bts)
        if a is None:
            a = {h: BucketAcc(bts) for h in self.horizons}
            self.accs[bts] = a
        for h in self.horizons:
            a[h].add(rec["ofi"], rec["tofi"], rec["bk"], rec["sk"],
                     fwd_dict[h])

    def _flush_closed(self, now):
        # a 60s bucket [bts, bts+bucket) is complete once we are past
        # bts + bucket + max_h, so no later record can still belong to it
        # (out-of-order tolerant; tolerates jitter up to max_h+bucket).
        cutoff = now - (self.bucket + self.max_h) * 1000
        for bts in list(self.accs.keys()):
            if bts <= cutoff:
                self._write_acc(self.accs.pop(bts))

    def _write_acc(self, accs):
        a0 = accs[self.horizons[0]]
        bk = a0.bk
        sk = a0.sk
        row = {"ts_bucket": a0.ts, "n": a0.n}
        for h in self.horizons:
            a = accs[h]
            row["ofi_hit_%ds" % h] = round(a.hit("ofi_hit"), 4)
            row["tofi_hit_%ds" % h] = round(a.hit("tofi_hit"), 4)
            row["agree_%ds" % h] = round(a.agree / a.agree_n, 4) \
                if a.agree_n else float("nan")
            row["comp05_hit_%ds" % h] = round(a.hit("comp05_hit"), 4)
            row["comp1_hit_%ds" % h] = round(a.hit("comp1_hit"), 4)
        row["bk_mean"] = round(sum(bk) / len(bk), 4) if bk else float("nan")
        row["bk_p95"] = round(_pct(bk, 95), 4)
        row["bk_max"] = round(max(bk), 4) if bk else float("nan")
        row["sk_mean"] = round(sum(sk) / len(sk), 4) if sk else float("nan")
        row["sk_p95"] = round(_pct(sk, 95), 4)
        row["sk_max"] = round(max(sk), 4) if sk else float("nan")
        self.w_main.writerow(row)
        self.f_main.flush()

        for _, _, lab in BREAKOUT_BINS:
            b = a0.bins[lab]
            if b["n"] == 0:
                continue
            brow = {"ts_bucket": a0.ts, "bin": lab, "n": b["n"]}
            for h in self.horizons:
                bh = accs[h].bins[lab]
                brow["ofi_hit_%ds" % h] = round(bh["ofi_hit"] / bh["ofi_hit_n"], 4) \
                    if bh["ofi_hit_n"] else float("nan")
                brow["tofi_hit_%ds" % h] = round(bh["tofi_hit"] / bh["tofi_hit_n"], 4) \
                    if bh["tofi_hit_n"] else float("nan")
                brow["agree_%ds" % h] = round(bh["agree"] / bh["agree_n"], 4) \
                    if bh["agree_n"] else float("nan")
            self.w_bin.writerow(brow)
        self.f_bin.flush()

    def close(self):
        if self.buffer:
            last = self.buffer[-1]
            while self.buffer:
                old = self.buffer.pop(0)
                fwd = {h: (last["mid"] / old["mid"] - 1.0)
                       if old["mid"] else 0.0 for h in self.horizons}
                self._accumulate(old, fwd)
        for bts in sorted(self.accs.keys()):
            self._write_acc(self.accs.pop(bts))
        self.f_main.close()
        self.f_bin.close()


async def processor_run(queue, engine, recorder):
    while True:
        event = await queue.get()
        et = event.get("type")
        ts = event.get("timestamp")
        if et == "book_updated":
            if not market_state.book_ready:
                continue
            feat = engine.update_book(market_state.orderbook, ts)
            if feat is not None:
                recorder.write(feat)
        elif et == "trade_updated":
            while market_state.trade_set:
                t = market_state.trade_set.popleft()
                feat = engine.update_trade(
                    t["price"], t["qty"], t["side"], t["timestamp"]
                )
                if feat is not None:
                    recorder.write(feat)
        elif et in ("book_error", "trade_error"):
            print(f"[monitor] {et}: {event.get('error')}")
        else:
            continue


async def main(prefix="data/monitor", bucket=60, horizons="1,5,10"):
    hz = tuple(int(x) for x in horizons.split(",") if x)
    print("Binance OrderFlow Monitor (multi-horizon: %s s)" % (hz,))
    queue = Queue()
    engine = OrderFlowEngine()
    recorder = MonitorRecorder(prefix=prefix, bucket=bucket, horizons=hz)

    depth_task = asyncio.create_task(orderbook_worker(queue))
    trade_task = asyncio.create_task(trade_worker(queue))
    proc_task = asyncio.create_task(processor_run(queue, engine, recorder))

    try:
        await asyncio.gather(depth_task, trade_task, proc_task)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("Stopping monitor...")
    finally:
        recorder.close()
        print("monitor files:\n  %s\n  %s" % (recorder.main_path, recorder.bin_path))


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="data/monitor")
    ap.add_argument("--bucket", type=int, default=60)
    ap.add_argument("--horizons", default="1,5,10,30")
    args = ap.parse_args()
    asyncio.run(main(args.prefix, args.bucket, args.horizons))
