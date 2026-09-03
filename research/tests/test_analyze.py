import numpy as np
import pandas as pd

from research import analyze


def _make_df(n=1000):
    rng = np.random.default_rng(0)
    t0 = 1_660_000_000_000
    ts = np.arange(n) * 1000 + t0
    mid = 100 + np.cumsum(rng.normal(0, 0.01, n))
    df = pd.DataFrame({
        'timestamp': ts,
        'mid': mid,
        'obi': rng.normal(0, 1, n),
        'trade_ofi': rng.normal(0, 1, n),
        'book_ofi': rng.normal(0, 1, n),
        'trend': rng.normal(0, 1, n),
        'bid_qty': 1.0,
        'ask_qty': 1.0,
    })
    return df


def test_add_forward_returns():
    df = analyze.add_forward_returns(_make_df())
    for h in analyze.HORIZONS_S:
        col = f'fwd_ret_{h}s'
        assert col in df.columns
        assert df[col].iloc[0] == 0.0 or not np.isnan(df[col].iloc[0])


def test_hit_rate_random_walk_about_50():
    df = analyze.add_forward_returns(_make_df())
    hr = analyze.hit_rate(df, indicator='obi', horizon_s=5)
    assert 0.0 <= hr['hit_rate'] <= 1.0
    assert 'n' in hr and 'p_value' in hr


def test_simple_strategy_returns_stats():
    df = analyze.add_forward_returns(_make_df())
    stats = analyze.simple_strategy(df, indicator='obi', horizon_s=5)
    for key in ['n_trades', 'win_rate', 'cum_profit', 'max_drawdown', 'sharpe']:
        assert key in stats
