import numpy as np
from scipy.stats import spearmanr

def rank_ic(signal: np.ndarray, forward_return: np.ndarray) -> float:
    m = np.isfinite(signal) & np.isfinite(forward_return)
    if m.sum() < 3:
        return np.nan
    c, _ = spearmanr(signal[m], forward_return[m])
    return float(c)

def icir(ic_series: np.ndarray) -> float:
    ic_series = np.asarray(ic_series, float)
    valid = ic_series[np.isfinite(ic_series)]
    if len(valid) < 3 or float(np.std(valid)) == 0:
        return np.nan
    return float(np.mean(valid) / np.std(valid))

def sharpe_ratio(returns: np.ndarray, periods_per_year: int = 252*1440) -> float:
    r = np.asarray(returns, float)
    r = r[np.isfinite(r)]
    if len(r) < 2 or float(np.std(r)) == 0:
        return np.nan
    return float(np.mean(r) / np.std(r) * np.sqrt(periods_per_year))

def sortino_ratio(returns: np.ndarray, periods_per_year: int = 252*1440) -> float:
    r = np.asarray(returns, float)
    r = r[np.isfinite(r)]
    downside = r[r < 0]
    if len(downside) < 2 or float(np.std(downside)) == 0:
        return np.nan
    return float(np.mean(r) / np.std(downside) * np.sqrt(periods_per_year))
