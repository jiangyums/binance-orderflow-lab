import numpy as np
from research.metrics_ic import rank_ic, icir, sharpe_ratio, sortino_ratio

def test_rank_ic_perfect():
    sig = np.array([1.,2.,3.,4.,5.]); ret = np.array([1.,2.,3.,4.,5.])
    assert abs(rank_ic(sig, ret) - 1.0) < 1e-9

def test_rank_ic_inverse():
    sig = np.array([1.,2.,3.,4.,5.]); ret = np.array([5.,4.,3.,2.,1.])
    assert abs(rank_ic(sig, ret) + 1.0) < 1e-9

def test_icir_stability():
    ics = np.array([0.05, 0.06, 0.04, 0.05, 0.06])
    assert icir(ics) > 2.0  # stable

def test_sharpe_positive():
    rets = np.array([0.01, 0.02, -0.005, 0.015])
    assert sharpe_ratio(rets) > 0
