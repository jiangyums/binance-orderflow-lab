import argparse
import bisect
import csv
import os
import sys

# Allow very large CSV fields (some feature columns can be big); the default
# 128KB limit would otherwise raise _csv.Error on legitimate data.
csv.field_size_limit(2_147_483_647)

# Make the repo root importable so the script runs without PYTHONPATH set.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orderflow.signal.engine import SignalEngine
from src.orderflow.signal.state_tracker import SignalStateTracker
from src.orderflow.statistics.signal_statistics import SignalStatistics


# Trade-OFI magnitude cutoffs (in BTC). The observed |tofi| distribution spans
# p50=0.002 .. p90=0.097 .. p99=0.68 .. max=30, so sweep from the tiny-noise
# regime up through the large-trade tail where the edge may actually clear cost.
THRESHOLDS = [0.0, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
DEFAULT_FEE = 0.0004  # per-side fee fraction (~0.04% taker on USD-M futures)


def _half_spread(spread, mid):
    """Half-spread as a fraction of mid (cost to cross one side)."""
    try:
        s = float(spread)
        m = float(mid)
    except (ValueError, TypeError):
        return 0.0
    if s <= 0 or m <= 0:
        return 0.0
    return s / (2.0 * m)


def replay_and_evaluate(
    features_path,
    threshold,
    tmp_path,
    fee,
    tofi_scale=1.0,
    tofi_mode="linear",
    tofi_rank_fn=None,
    tofi_top_pct=0.0,
):
    """Replay a FIXED features.csv through the trade-OFI pipeline at one emit
    threshold (min |tofi| to fire a signal).

    Returns the eval CSV path and the average round-trip cost fraction per
    horizon. Signal selection reuses the exact SignalEngine code; returns are
    computed by binary search on the price timeline (equivalent to
    SignalEvaluator's 'first price with diff >= horizon' rule). Cost is derived
    from the REAL recorded spread (half-spread entry + exit + 2 x fee).
    """

    eng = SignalEngine(
        tofi_threshold=threshold,
        tofi_scale=tofi_scale,
        tofi_mode=tofi_mode,
        tofi_rank_fn=tofi_rank_fn,
    )
    tracker = SignalStateTracker(emit_flat=True)

    rows = []
    with open(features_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            feat = {}
            for k, v in row.items():
                if k == "timestamp":
                    feat[k] = int(v)
                else:
                    try:
                        feat[k] = float(v)
                    except (ValueError, TypeError):
                        feat[k] = v  # keep non-numeric (e.g. trade_side)
            rows.append(feat)

    # Depth/trade websockets arrive out of order, so rows are NOT time-sorted.
    # The bisect-based forward-return lookup below requires an ascending
    # timeline, so sort by timestamp first (same root cause as the monitor
    # fragmentation bug).
    rows.sort(key=lambda r: r["timestamp"])

    timestamps = [r["timestamp"] for r in rows]
    mids = [r["mid"] for r in rows]
    spreads = [r.get("spread", 0.0) for r in rows]

    # replay engine + tracker to get the exact emitted signal set
    signals = []
    for feat in rows:
        sig = eng.generate(feat)
        if sig is None:
            continue
        filtered = tracker.update(sig)
        if filtered is None:
            continue
        signals.append(
            {
                "timestamp": filtered.timestamp,
                "signal": filtered.side.value,
                "strength": filtered.strength,
                "entry": feat["mid"],
                "spread": feat.get("spread", 0.0),
                "tofi": abs(float(feat.get("tofi", 0.0))),
            }
        )

    if tofi_top_pct > 0 and signals:
        em = sorted(s["tofi"] for s in signals)
        cutoff = em[int((100.0 - tofi_top_pct) / 100.0 * (len(em) - 1))]
        signals = [s for s in signals if s["tofi"] >= cutoff]

    sum_cost = [0.0, 0.0, 0.0]  # 1s, 5s, 10s
    count = 0

    # evaluate each signal against future prices + real spread cost
    with open(tmp_path, "w", newline="", encoding="utf-8") as out:
        w = csv.DictWriter(
            out,
            fieldnames=[
                "signal_time",
                "signal",
                "strength",
                "entry_price",
                "return_1s",
                "return_5s",
                "return_10s",
            ],
        )
        w.writeheader()
        for s in signals:
            t0 = s["timestamp"]
            entry = s["entry"]
            half_entry = _half_spread(s["spread"], entry)

            gross = {}
            costs = {}
            complete = True
            for horizon, key in (
                (1000, "return_1s"),
                (5000, "return_5s"),
                (10000, "return_10s"),
            ):
                idx = bisect.bisect_left(timestamps, t0 + horizon)
                if idx >= len(timestamps):
                    complete = False
                    break
                gross[key] = (mids[idx] - entry) / entry
                half_exit = _half_spread(spreads[idx], mids[idx])
                costs[key] = half_entry + half_exit + 2.0 * fee

            if not complete:
                continue

            w.writerow(
                {
                    "signal_time": t0,
                    "signal": s["signal"],
                    "strength": s["strength"],
                    "entry_price": entry,
                    "return_1s": gross["return_1s"],
                    "return_5s": gross["return_5s"],
                    "return_10s": gross["return_10s"],
                }
            )
            count += 1
            for key, ci in (
                ("return_1s", 0),
                ("return_5s", 1),
                ("return_10s", 2),
            ):
                sum_cost[ci] += costs[key]

    avg_cost = [c / count for c in sum_cost] if count else [0.0, 0.0, 0.0]
    return tmp_path, avg_cost


def aggregate(eval_path):
    stats = SignalStatistics()
    stats.load(eval_path)

    rows = [x for x in stats.data if x["signal"] in ("LONG", "SHORT")]
    n = len(rows)
    if n == 0:
        return n, (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)

    def overall(horizon):
        wins = sum(
            1
            for x in rows
            if (x["signal"] == "LONG" and x[horizon] > 0)
            or (x["signal"] == "SHORT" and x[horizon] < 0)
        )
        avg = sum(stats._pnl(x, horizon) for x in rows) / n
        return wins / n, avg

    w1, a1 = overall("return_1s")
    w5, a5 = overall("return_5s")
    w10, a10 = overall("return_10s")
    return n, (w1, a1), (w5, a5), (w10, a10)


def _build_tofi_rank_fn(path):
    vals = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                vals.append(abs(float(row["tofi"])))
            except (ValueError, TypeError, KeyError):
                pass
    vals.sort()
    n = len(vals)
    if n == 0:
        return lambda x: 0.0
    return lambda x: bisect.bisect_right(vals, x) / n


def main():
    ap = argparse.ArgumentParser(
        description="Trade-OFI Threshold Sweep: replay a fixed features.csv at "
        "multiple emit thresholds (min |tofi| to fire a signal)."
    )
    ap.add_argument(
        "--features",
        default="data/features.csv",
        help="fixed recorded feature dataset (one session, ideally at tofi_threshold=0.0)",
    )
    ap.add_argument(
        "--thresholds",
        type=float,
        nargs="*",
        default=THRESHOLDS,
    )
    ap.add_argument(
        "--fee",
        type=float,
        default=DEFAULT_FEE,
        help="per-side fee fraction, e.g. 0.0004 = 0.04%% taker (0.0002 maker)",
    )
    ap.add_argument(
        "--tofi-scale",
        type=float,
        default=1.0,
        help="trade-OFI strength divisor: strength=min(|tofi|/scale,1)",
    )
    ap.add_argument(
        "--tofi-mode",
        default="linear",
        choices=["linear", "rank"],
        help="trade-OFI strength mode: linear (scalar) or rank (percentile of |tofi|)",
    )
    ap.add_argument(
        "--tofi-top-pct",
        type=float,
        default=0.0,
        help="if >0, only trade signals whose |tofi| is in the top P%% of the session",
    )
    args = ap.parse_args()

    if not os.path.exists(args.features):
        print("features file not found: %s" % args.features)
        print("record one session first: python -m src.orderflow.collector.main")
        return

    print(
        "\nTrade-OFI Threshold Sweep  (dataset: %s, fee=%.3f%%/side)\n"
        % (args.features, args.fee * 100)
    )
    print(
        "%-8s %-8s %-7s %-9s %-9s %-7s %-9s %-9s %-8s %-10s %-10s %-9s"
        % (
            "thr",
            "samples",
            "win1%",
            "ret1",
            "net1",
            "win5%",
            "ret5",
            "net5",
            "win10%",
            "ret10",
            "net10",
            "cost",
        )
    )
    print("-" * 111)

    tmp_dir = "data/_sweep_tmp"
    os.makedirs(tmp_dir, exist_ok=True)

    tofi_rank_fn = None
    if args.tofi_mode == "rank":
        tofi_rank_fn = _build_tofi_rank_fn(args.features)

    for thr in args.thresholds:
        tmp = os.path.join(tmp_dir, "T%s.csv" % thr)
        tmp, (c1, c5, c10) = replay_and_evaluate(
            args.features,
            thr,
            tmp,
            args.fee,
            args.tofi_scale,
            args.tofi_mode,
            tofi_rank_fn,
            args.tofi_top_pct,
        )
        n, (w1, a1), (w5, a5), (w10, a10) = aggregate(tmp)
        net1 = a1 - c1
        net5 = a5 - c5
        net10 = a10 - c10
        cost_avg = (c1 + c5 + c10) / 3.0
        print(
            "%-8.4f %-8d %-7.1f%% %-9.5f %-9.5f %-7.1f%% %-9.5f %-9.5f %-8.1f%% %-10.5f %-10.5f %-9.5f"
            % (
                thr,
                n,
                w1 * 100,
                a1,
                net1,
                w5 * 100,
                a5,
                net5,
                w10 * 100,
                a10,
                net10,
                cost_avg,
            )
        )
        os.remove(tmp)

    print(
        "\nnet_Xs = avg_ret_Xs - cost_Xs, where cost_Xs = half-spread@entry "
        "+ half-spread@exit + 2xfee, derived from the recorded spread."
    )
    print(
        "avg round-trip cost ~= %.3f%% (fee=%.3f%% per side)"
        % (cost_avg * 100, args.fee * 100)
    )


if __name__ == "__main__":
    main()
