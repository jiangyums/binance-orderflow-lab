import argparse
import bisect
import csv
import os

from src.orderflow.signal.engine import SignalEngine
from src.orderflow.signal.state_tracker import SignalStateTracker
from src.orderflow.statistics.signal_statistics import SignalStatistics


THRESHOLDS = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
COST = 0.001  # ~0.1% round-trip (fee + spread), for net-PnL view


def replay_and_evaluate(features_path, threshold, tmp_path):
    """Replay a FIXED features.csv through the production pipeline at one emit
    threshold.

    Returns the eval CSV path. The signal set is produced by reusing the exact
    SignalEngine + SignalStateTracker code; returns are computed by binary
    search on the price timeline (equivalent to SignalEvaluator's 'first price
    with diff >= horizon' rule), which is O(N log N) instead of the evaluator's
    O(pending * prices) per-row cost that is only acceptable in real-time.
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
            }
        )

    # evaluate each signal against future prices
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
            fut = {}
            for horizon, key in (
                (1000, "return_1s"),
                (5000, "return_5s"),
                (10000, "return_10s"),
            ):
                idx = bisect.bisect_left(timestamps, t0 + horizon)
                if idx < len(timestamps):
                    fut[key] = (mids[idx] - entry) / entry
            if len(fut) == 3:
                w.writerow(
                    {
                        "signal_time": t0,
                        "signal": s["signal"],
                        "strength": s["strength"],
                        "entry_price": entry,
                        "return_1s": fut["return_1s"],
                        "return_5s": fut["return_5s"],
                        "return_10s": fut["return_10s"],
                    }
                )

    return tmp_path


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
        "--cost",
        type=float,
        default=COST,
        help="round-trip cost for net-PnL view (fraction)",
    )
    args = ap.parse_args()

    if not os.path.exists(args.features):
        print("features file not found: %s" % args.features)
        print("record one session first: python -m src.orderflow.collector.main")
        return

    print(
        "\nThreshold Sweep  (dataset: %s, cost=%.3f%%)\n"
        % (args.features, args.cost * 100)
    )
    print(
        "%-6s %-8s %-8s %-10s %-8s %-10s %-8s %-10s %-12s"
        % (
            "thr", "samples", "win_1s", "avg_ret_1s",
            "win_5s", "avg_ret_5s", "win_10s", "avg_ret_10s",
            "net_avg_10s",
        )
    )
    print("-" * 92)

    tmp_dir = "data/_sweep_tmp"
    os.makedirs(tmp_dir, exist_ok=True)

    for thr in args.thresholds:
        tmp = os.path.join(tmp_dir, "T%s.csv" % thr)
        replay_and_evaluate(args.features, thr, tmp)
        n, (w1, a1), (w5, a5), (w10, a10) = aggregate(tmp)
        net10 = a10 - args.cost
        print(
            "%-6.1f %-8d %-7.1f%% %-10.5f %-7.1f%% %-10.5f %-7.1f%% %-10.5f %-12.5f"
            % (
                thr, n,
                w1 * 100, a1,
                w5 * 100, a5,
                w10 * 100, a10,
                net10,
            )
        )
        os.remove(tmp)

    print("\n(net_avg_10s = avg_ret_10s - cost; >0 means profitable after fees)")


if __name__ == "__main__":
    main()
