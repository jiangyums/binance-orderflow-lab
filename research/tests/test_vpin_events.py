# research/tests/test_vpin_events.py
import numpy as np
from research.vpin_events import normalize_cdf, detect_vpin_events

def test_normalize_cdf_range():
    vpin = np.array([0.2, 0.3, 0.25, 0.4, 0.35])
    cdf = normalize_cdf(vpin)
    assert np.all(cdf >= 0) and np.all(cdf <= 1)

def test_detect_crossing():
    # CDF crosses 0.9 from below at index 2
    vpin = np.array([0.1, 0.2, 0.9, 0.95, 0.8, 0.1])
    events = detect_vpin_events(vpin, threshold=0.9, exit_threshold=0.5)
    assert len(events) == 1
    assert events[0][0] == 2

def test_no_event_when_always_high():
    vpin = np.ones(20) * 0.5
    events = detect_vpin_events(vpin, threshold=0.99, exit_threshold=0.85)
    assert len(events) == 0
