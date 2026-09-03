import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from research import config

HORIZONS_S = config.FUTURE_HORIZONS_S
INDICATORS = ['obi', 'trade_ofi', 'book_ofi', 'trend']


def add_forward_returns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values('timestamp').reset_index(drop=True)
    mids = df['mid'].to_numpy()
    for h in HORIZONS_S:
        col = f'fwd_ret_{h}s'
        shifted = np.full(len(mids), np.nan)
        shifted[:-h] = mids[h:]  # 数据 1s 间隔，h 秒 = h 行之后
        df[col] = (shifted - mids) / mids
    return df


def _drop_small_abs(df, indicator, frac=config.DROP_SMALL_ABS_FRAC):
    threshold = df[indicator].abs().quantile(frac)
    return df[df[indicator].abs() >= threshold]


def hit_rate(df, indicator, horizon_s):
    sub = _drop_small_abs(df.dropna(subset=[indicator, f'fwd_ret_{horizon_s}s']), indicator)
    # 剔除平局样本：价格未动（ret == 0）时无方向可命中，不应计入 miss
    sub = sub[sub[f'fwd_ret_{horizon_s}s'] != 0]
    if len(sub) == 0:
        return {'indicator': indicator, 'horizon_s': horizon_s,
                'hit_rate': np.nan, 'n': 0, 'p_value': np.nan}
    sign_match = np.sign(sub[indicator].to_numpy()) == np.sign(sub[f'fwd_ret_{horizon_s}s'].to_numpy())
    n = len(sign_match)
    k = int(sign_match.sum())
    p_value = sp_stats.binomtest(k, n, 0.5, alternative='greater').pvalue
    return {'indicator': indicator, 'horizon_s': horizon_s,
            'hit_rate': k / n, 'n': n, 'p_value': p_value}


def hit_rate_table(df) -> pd.DataFrame:
    rows = []
    for ind in INDICATORS:
        for h in HORIZONS_S:
            rows.append(hit_rate(df, ind, h))
    return pd.DataFrame(rows)


def quantile_groups(df, indicator, horizon_s, q=5):
    sub = df.dropna(subset=[indicator, f'fwd_ret_{horizon_s}s']).copy()
    sub['bucket'] = pd.qcut(sub[indicator], q, labels=False, duplicates='drop')
    rows = []
    for b, g in sub.groupby('bucket'):
        rows.append({
            'bucket': int(b),
            'mean_ret': g[f'fwd_ret_{horizon_s}s'].mean(),
            'std_ret': g[f'fwd_ret_{horizon_s}s'].std(),
            'n': len(g),
        })
    return pd.DataFrame(rows)


def simple_strategy(df, indicator, horizon_s,
                    z_window_s=config.Z_WINDOW_S,
                    threshold=config.Z_THRESHOLD,
                    cost=config.ROUND_TRIP_COST):
    df = df.sort_values('timestamp').reset_index(drop=True)
    col = df[indicator]
    z = (col - col.rolling(z_window_s, min_periods=z_window_s).mean()) / col.rolling(
        z_window_s, min_periods=z_window_s).std()

    trades = []  # (entry, exit, side, ret)
    i = 0
    n = len(df)
    while i < n:
        zi = z.iloc[i]
        if pd.isna(zi) or abs(zi) <= threshold:
            i += 1
            continue
        side = 1.0 if zi > 0 else -1.0
        entry = df['mid'].iloc[i]
        j = i + horizon_s
        if j >= n:
            break
        exit_ = df['mid'].iloc[j]
        gross = side * (exit_ - entry) / entry
        net = gross - cost
        trades.append({'entry': entry, 'exit': exit_, 'side': side,
                       'gross_ret': gross, 'net_ret': net})
        i = j + 1  # 持仓期间不重复开仓

    if not trades:
        return {'indicator': indicator, 'horizon_s': horizon_s, 'n_trades': 0,
                'win_rate': np.nan, 'cum_profit': np.nan, 'max_drawdown': np.nan, 'sharpe': np.nan}

    t = pd.DataFrame(trades)
    n_trades = len(t)
    win_rate = (t['net_ret'] > 0).mean()
    cum = t['net_ret'].cumsum()
    peak = cum.cummax()
    drawdown = cum - peak
    # 近似年化：假设每秒最多一笔交易（实际上信号稀疏），为日胜率 Sharpe 上界
    sharpe = t['net_ret'].mean() / t['net_ret'].std() * np.sqrt(config.SECONDS_PER_DAY / horizon_s) if t['net_ret'].std() > 0 else np.nan
    return {
        'indicator': indicator, 'horizon_s': horizon_s, 'n_trades': n_trades,
        'win_rate': win_rate, 'cum_profit': cum.iloc[-1], 'max_drawdown': drawdown.min(),
        'sharpe': sharpe,
    }


def strategy_table(df) -> pd.DataFrame:
    rows = []
    for ind in INDICATORS:
        for h in HORIZONS_S:
            rows.append(simple_strategy(df, ind, h))
    return pd.DataFrame(rows)
