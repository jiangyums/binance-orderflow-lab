import numpy as np
from research.vpin_prediction_quality import classify_events, compute_metrics, naive_classifier

def test_classify_tp_fp():
    vpin_events = [(0, 5), (20, 25)]
    mir = np.zeros(50); mir[10] = 0.05  # only first event has high MIR after it
    results = classify_events(vpin_events, mir, mir_threshold=0.02, event_horizon=10)
    assert results[0]['is_true_positive'] is True
    assert results[1]['is_true_positive'] is False

def test_metrics_fpr():
    classified = [{'is_true_positive': True}, {'is_true_positive': False}, {'is_true_positive': False}]
    m = compute_metrics(classified)
    assert abs(m['fpr'] - 2/3) < 1e-9
    assert abs(m['precision'] - 1/3) < 1e-9

def test_naive_deterministic():
    mir = np.random.RandomState(0).randn(1000)
    a = naive_classifier(10, 1000, mir, 0.02, event_horizon=20)
    b = naive_classifier(10, 1000, mir, 0.02, event_horizon=20)
    assert a == b  # fixed seed
