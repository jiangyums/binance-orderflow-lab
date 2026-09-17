import numpy as np
from research.mir import compute_mir, compute_mir_batch

def test_mir_monotonic_up():
    assert compute_mir(np.array([100., 101., 102.])) == 102/100-1

def test_mir_monotonic_down():
    assert compute_mir(np.array([102., 101., 100.])) == 100/102-1

def test_mir_v_pattern():
    # 100->94->100: max swing 6%
    m = compute_mir(np.array([100., 94., 100.]))
    assert abs(m) == abs(100/94-1)

def test_mir_batch_length():
    prices = np.array([100., 101., 99., 102., 98.])
    out = compute_mir_batch(prices, window_size=3)
    assert len(out) == len(prices)
    assert np.isnan(out[0]) and np.isnan(out[1])
    assert np.isfinite(out[2])
