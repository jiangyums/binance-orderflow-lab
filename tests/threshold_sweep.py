import argparse
import bisect
import csv
import os

from src.orderflow.signal.engine import SignalEngine
from src.orderflow.signal.state_tracker import SignalStateTracker
from src.orderflow.statistics.signal_statistics import SignalStatistics


THRESHOLDS = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
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


def replay_and_evaluate(features_path, threshold, tmp_path, fee):
    """Replay a FIXED features.csv through the production pipeline at one emit
    threshold.

    Returns the eval CSV path and the average round-trip cost fraction per
    horizon. Signal selection reuses the exact SignalEngine + SignalStateTracker
    code; returns are computed by binary search on the price timeline
    (equivalent to SignalEvaluator's 'first price with diff >= horizon' rule).
    Cost is derived from the REAL recorded spread (half-spread entry + exit +
    2 x fee), not a flat guess.
    """

    eng = SignalEngine(threshold=threshold)
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
            }
        )

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

    rows = [
        x for x in stats.data
        if x["signal"] in ("LONG", "SHORT")
    ]
    n = len(rows)
    if n == 0:
        return n, (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)

    def overall(horizon):
        wins = sum(
            1 for x in rows
            if (x["signal"] == "LONG" and x[horizon] > 0)
            or (x["signal"] == "SHORT" and x[horizon] < 0)
        )
        avg = sum(stats._pnl(x, horizon) for x in rows) / n
        return wins / n, avg

    w1, a1 = overall("return_1s")
    w5, a5 = overall("return_5s")
    w10, a10 = overall("return_10s")
    return n, (w1, a1), (w5, a5), (w10, a10)


def main():
    ap = argparse.ArgumentParser(
        description="Threshold Sweep: replay a fixed features.csv at multiple emit thresholds."
    )
    ap.add_argument(
        "--features",
        default="data/features.csv",
        help="fixed recorded feature dataset (one batch)",
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
    args = ap.parse_args()

    if not os.path.exists(args.features):
        print("features file not found: %s" % args.features)
        print("record one session first: python -m src.orderflow.collector.main")
        return

    print(
        "\nThreshold Sweep  (dataset: %s, fee=%.3f%%/side)\n"
        % (args.features, args.fee * 100)
    )
    print(
        "%-5s %-8s %-7s %-9s %-9s %-7s %-9s %-9s %-8s %-10s %-10s %-9s"
        % (
            "thr", "samples", "win1%", "ret1", "net1",
            "win5%", "ret5", "net5", "win10%", "ret10", "net10", "cost",
        )
    )
    print("-" * 111)

    tmp_dir = "data/_sweep_tmp"
    os.makedirs(tmp_dir, exist_ok=True)

    for thr in args.thresholds:
        tmp = os.path.join(tmp_dir, "T%s.csv" % thr)
        tmp, (c1, c5, c10) = replay_and_evaluate(
            args.features, thr, tmp, args.fee
        )
        n, (w1, a1), (w5, a5), (w10, a10) = aggregate(tmp)
        net1 = a1 - c1
        net5 = a5 - c5
        net10 = a10 - c10
        cost_avg = (c1 + c5 + c10) / 3.0
        print(
            "%-5.1f %-8d %-7.1f%% %-9.5f %-9.5f %-7.1f%% %-9.5f %-9.5f %-8.1f%% %-10.5f %-10.5f %-9.5f"
            % (
                thr, n,
                w1 * 100, a1, net1,
                w5 * 100, a5, net5,
                w10 * 100, a10, net10,
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
