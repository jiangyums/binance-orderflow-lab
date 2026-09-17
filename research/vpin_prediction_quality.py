"""
VPIN Prediction Quality — Wu et al. (2013) method.

Evaluates VPIN using MIR (Maximum Intermediate Return) as ground truth.
Computes FPR, Precision, Recall, and compares with naive classifier.

Refactored to reuse canonical modules:
  - research.mir: compute_mir, compute_mir_batch
  - research.vpin_events: normalize_cdf, detect_vpin_events
"""
import numpy as np
import pandas as pd
from pathlib import Path
import zipfile

from research.mir import compute_mir, compute_mir_batch
from research.vpin_events import normalize_cdf, detect_vpin_events

OUT_DIR = Path('data/hist/vpin')
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Classification
# ============================================================================

def classify_events(vpin_events, mir_values, mir_threshold=None, event_horizon=50):
    """
    Classify VPIN events as TP/FP using MIR as ground truth.

    For each VPIN event:
        1. Look at MIR values in the window [event_end, event_end + event_horizon]
        2. If max |MIR| in that window > mir_threshold -> True Positive
        3. Otherwise -> False Positive

    Args:
        vpin_events: list of (start, end) index pairs
        mir_values: MIR time series (same length as VPIN)
        mir_threshold: threshold for "high volatility" event (default: mean + 2*std)
        event_horizon: how many buckets to look ahead after VPIN event ends

    Returns: list of dicts with event details
    """
    if mir_threshold is None:
        valid = mir_values[np.isfinite(mir_values)]
        mir_threshold = float(np.mean(np.abs(valid)) + 2 * np.std(np.abs(valid)))
    out = []
    n = len(mir_values)
    for s, e in vpin_events:
        ls = e + 1
        le = min(ls + event_horizon, n)
        if ls >= n:
            continue
        win = mir_values[ls:le]
        valid = win[np.isfinite(win)]
        if len(valid) == 0:
            continue
        max_abs = float(np.max(np.abs(valid)))
        out.append({
            'start': s,
            'end': e,
            'look_start': ls,
            'look_end': le,
            'max_abs_mir': max_abs,
            'mir_threshold': mir_threshold,
            'is_true_positive': bool(max_abs > mir_threshold),
        })
    return out


def compute_metrics(classified):
    """Compute FPR, Precision, Recall from classified events."""
    tp = sum(1 for e in classified if e['is_true_positive'])
    fp = sum(1 for e in classified if not e['is_true_positive'])
    total = len(classified)
    if total == 0:
        return {'tp': 0, 'fp': 0, 'fn': 0, 'fpr': 0, 'precision': 0, 'recall': 0, 'f1': 0}
    prec = tp / (tp + fp) if tp + fp > 0 else 0
    return {'tp': tp, 'fp': fp, 'fn': 0, 'fpr': fp / total, 'precision': prec, 'recall': 0, 'f1': 0}


# ============================================================================
# Naive Classifier (Baseline) — fixed seed per Bambade 2018
# ============================================================================

def naive_classifier(n_events, n_total, mir_values, mir_threshold, event_horizon=50):
    """
    Random baseline: randomly select n_events time points,
    check how often MIR is high in the following window.
    Fixed seed (42) for reproducibility.
    """
    if n_events == 0 or n_total == 0:
        return {'fpr': 0, 'precision': 0}
    rng = np.random.RandomState(42)
    n_choices = max(1, n_total - event_horizon)
    size = min(n_events, n_choices)
    starts = rng.choice(n_choices, size=size, replace=False)
    tp = 0
    for s in starts:
        win = mir_values[s:s + event_horizon]
        valid = win[np.isfinite(win)]
        if len(valid) > 0 and float(np.max(np.abs(valid))) > mir_threshold:
            tp += 1
    prec = tp / n_events if n_events > 0 else 0
    return {'fpr': 1 - prec, 'precision': prec}


# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 70)
    print("VPIN Prediction Quality — Wu et al. (2013) Method")
    print("=" * 70)

    # Load kline data (for trade-level prices)
    km = np.load('data/hist/klines/BTCUSDT-1m_full.npz', allow_pickle=True)['data']
    kline_times = pd.to_datetime(km['exch_ts'], unit='ns')
    kline_prices = km['px']

    # Load all valid 2025 trades
    trade_dir = Path('data/hist/trades')
    zips = sorted(trade_dir.glob('BTCUSDT-trades-2025-*.zip'))

    all_prices = []
    all_qty = []
    all_signs = []

    for z in zips:
        try:
            with zipfile.ZipFile(str(z)) as zf:
                zf.testzip()
                with zf.open(zf.namelist()[0]) as f:
                    raw = f.read().decode('utf-8')
        except Exception:
            continue

        lines = raw.split('\n')
        parsed = [l.split(',') for l in lines[1:] if l.strip() and len(l.split(',')) >= 6]
        if not parsed:
            continue

        data = np.array(parsed, dtype=object)
        all_prices.append(data[:, 1].astype(np.float64))
        all_qty.append(data[:, 2].astype(np.float64))
        signs = np.where(data[:, 5] == 'True', -1, 1).astype(np.int8)
        all_signs.append(signs)

    prices = np.concatenate(all_prices)
    qty = np.concatenate(all_qty)
    signs = np.concatenate(all_signs)

    print(f"\nTotal trades: {len(prices):,}, total volume: {qty.sum():.0f} BTC")

    # Compute VPIN (bucket_volume=50, window=20)
    bucket_volume = 50.0
    vpin_window = 20

    cum_qty = np.cumsum(qty)
    n_full = int(cum_qty[-1] // bucket_volume)
    bucket_levels = np.arange(1, n_full + 1) * bucket_volume
    bucket_end_trades = np.searchsorted(cum_qty, bucket_levels, side='right')
    bnd_idx = bucket_end_trades - 1
    prev_idx = np.concatenate([[-1], bnd_idx[:-1]])

    signed_qty = qty * signs
    cum_signed = np.cumsum(signed_qty)
    cum_abs_qty = np.cumsum(np.abs(qty))

    abs_end = cum_abs_qty[bnd_idx]
    signed_end = cum_signed[bnd_idx]
    abs_prev = np.where(prev_idx >= 0, cum_abs_qty[prev_idx], 0)
    signed_prev = np.where(prev_idx >= 0, cum_signed[prev_idx], 0)

    buy_vol = (abs_end - abs_prev + signed_end - signed_prev) / 2.0
    sell_vol = (abs_end - abs_prev - signed_end + signed_prev) / 2.0
    imbalance = np.abs(buy_vol - sell_vol)
    vol = buy_vol + sell_vol

    imp_series = pd.Series(imbalance).rolling(vpin_window).mean().values
    vol_series = pd.Series(vol).rolling(vpin_window).mean().values
    vpin = imp_series / vol_series

    print(f"Buckets: {n_full}, valid VPIN: {np.isfinite(vpin).sum()}")

    # Compute MIR on bucket-level prices (bucket end trade prices)
    bucket_prices = prices[bnd_idx]
    print(f"Computing MIR (window=50 buckets)...", flush=True)
    mir = compute_mir_batch(bucket_prices, window_size=50)
    print(f"Valid MIR: {np.isfinite(mir).sum()}")

    # MIR threshold: mean + 2*std of |MIR|
    valid_mir = np.abs(mir[np.isfinite(mir)])
    mir_threshold = np.mean(valid_mir) + 2 * np.std(valid_mir)
    print(f"MIR threshold: {mir_threshold:.6f} (mean={np.mean(valid_mir):.6f}, std={np.std(valid_mir):.6f})")

    # Detect VPIN events for different thresholds
    print(f"\n{'='*70}")
    print("VPIN EVENT DETECTION AND CLASSIFICATION")
    print(f"{'='*70}")

    for theta in [0.90, 0.95, 0.99]:
        events = detect_vpin_events(vpin, threshold=theta, exit_threshold=0.85)
        if not events:
            print(f"\n  theta={theta}: No events detected")
            continue

        classified = classify_events(events, mir, mir_threshold=mir_threshold, event_horizon=50)
        metrics = compute_metrics(classified)

        # Naive baseline
        naive = naive_classifier(len(events), len(vpin), mir, mir_threshold, event_horizon=50)

        print(f"\n  theta={theta}:")
        print(f"    VPIN events: {len(events)}")
        print(f"    True Positives:  {metrics['tp']}")
        print(f"    False Positives: {metrics['fp']}")
        print(f"    FPR:             {metrics['fpr']:.4f}")
        print(f"    Precision:       {metrics['precision']:.4f}")
        print(f"    Naive FPR:       {naive['fpr']:.4f}")
        print(f"    Naive Precision: {naive['precision']:.4f}")
        print(f"    VPIN vs Naive:   {'BETTER' if metrics['precision'] > naive['precision'] else 'WORSE or EQUAL'}")

    # Sensitivity: vary event_horizon
    print(f"\n{'='*70}")
    print("SENSITIVITY: Event Horizon")
    print(f"{'='*70}")

    events_99 = detect_vpin_events(vpin, threshold=0.99, exit_threshold=0.85)
    if events_99:
        for horizon in [10, 20, 50, 100, 200]:
            classified = classify_events(events_99, mir, mir_threshold=mir_threshold, event_horizon=horizon)
            metrics = compute_metrics(classified)
            print(f"  horizon={horizon:3d}: events={len(events_99):3d}  "
                  f"TP={metrics['tp']:3d}  FP={metrics['fp']:3d}  "
                  f"FPR={metrics['fpr']:.4f}  Precision={metrics['precision']:.4f}")

    # Sensitivity: vary VPIN window
    print(f"\n{'='*70}")
    print("SENSITIVITY: VPIN Rolling Window")
    print(f"{'='*70}")

    for vw in [10, 20, 30, 50]:
        imp_s = pd.Series(imbalance).rolling(vw).mean().values
        vol_s = pd.Series(vol).rolling(vw).mean().values
        vpin_vw = imp_s / vol_s
        events_vw = detect_vpin_events(vpin_vw, threshold=0.99, exit_threshold=0.85)
        if not events_vw:
            print(f"  window={vw:2d}: No events")
            continue
        classified_vw = classify_events(events_vw, mir, mir_threshold=mir_threshold, event_horizon=50)
        m_vw = compute_metrics(classified_vw)
        print(f"  window={vw:2d}: events={len(events_vw):3d}  "
              f"TP={m_vw['tp']:3d}  FP={m_vw['fp']:3d}  "
              f"FPR={m_vw['fpr']:.4f}  Precision={m_vw['precision']:.4f}")

    print(f"\nDone. Saved nothing (run vpin_validity.py for full output).")


if __name__ == '__main__':
    main()
