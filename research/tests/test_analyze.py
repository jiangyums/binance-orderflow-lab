import numpy as np
import pandas as pd

from research import analyze


def _make_df(n=2000):
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
    mids = df['mid'].to_numpy()
    for h in analyze.HORIZONS_S:
        col = f'fwd_ret_{h}s'
        assert col in df.columns
        expected_first = (mids[h] - mids[0]) / mids[0]
        assert np.isclose(df[col].iloc[0], expected_first)
        # tail h rows must be NaN
        assert df[col].iloc[-h:].isna().all()


def test_hit_rate_random_walk_about_50():
    df = analyze.add_forward_returns(_make_df())
    hr = analyze.hit_rate(df, indicator='obi', horizon_s=5)
    assert 0.4 < hr['hit_rate'] < 0.6
    assert hr['n'] > 1000


def test_hit_rate_excludes_zero_return_ties():
    # 平局剔除：fwd_ret == 0 的样本不应计入 n
    df = _make_df()
    df.loc[500:800, 'mid'] = 500.0
    df = analyze.add_forward_returns(df)  # 改 mid 后重算 fwd_ret
    hr = analyze.hit_rate(df, indicator='obi', horizon_s=5)
    df_ref = analyze.add_forward_returns(_make_df())
    hr_ref = analyze.hit_rate(df_ref, indicator='obi', horizon_s=5)
    # 平局区间 296 行被剔除而非计为 miss
    assert hr['n'] < hr_ref['n']
    assert hr_ref['n'] - hr['n'] > 200


def test_simple_strategy_returns_stats():
    df = analyze.add_forward_returns(_make_df())
    stats = analyze.simple_strategy(df, indicator='obi', horizon_s=5)
    for key in ['n_trades', 'win_rate', 'cum_profit', 'max_drawdown', 'sharpe']:
        assert key in stats
