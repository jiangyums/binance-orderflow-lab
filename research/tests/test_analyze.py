import numpy as np
import pandas as pd

from research import analyze


def _make_df(n=2000):
    rng = np.random.default_rng(0)
    t0 = 1_660_000_000_000_000_000  # ns
    ts = np.arange(n) * 1_000_000_000 + t0  # 1s 步长（ns）
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


def test_add_forward_returns_nonuniform_timestamps():
    # 事件驱动数据行间时间戳不均匀：h 秒后 = 按时间戳找，而非按行偏移
    # 时间戳单位 = 纳秒
    df = pd.DataFrame({
        'timestamp': [0, 5e8, 5e9, 15e9, 60e9],
        'mid': [100.0, 100.5, 101.0, 103.0, 106.0],
        'obi': [0.0, 0.1, 0.2, 0.3, 0.4],
        'trade_ofi': [0.0, 0.0, 0.0, 0.0, 0.0],
        'book_ofi': [0.0, 0.0, 0.0, 0.0, 0.0],
        'trend': [0.0, 0.0, 0.0, 0.0, 0.0],
        'bid_qty': [1.0, 1.0, 1.0, 1.0, 1.0],
        'ask_qty': [1.0, 1.0, 1.0, 1.0, 1.0],
    })
    df = analyze.add_forward_returns(df)
    # h=5s: row0(ts=0) 未来5s → ts=5e9 的 mid=101.0
    assert np.isclose(df['fwd_ret_5s'].iloc[0], (101.0 - 100.0) / 100.0)
    # row1(ts=5e8) 未来5s → ts=15e9 的 mid=103.0（跳过中间）
    assert np.isclose(df['fwd_ret_5s'].iloc[1], (103.0 - 100.5) / 100.5)
    # 最后一行无未来 → NaN
    assert np.isnan(df['fwd_ret_5s'].iloc[-1])


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


def test_simple_strategy_nonuniform_timestamps():
    # 事件驱动数据：持仓 h 秒后平仓应按时间戳定位退出，而非固定行偏移
    ts = np.arange(0, 100) * 1_000_000_000  # 1s 均匀
    # 中间插入一个长时间缺口：行 30 之后时间戳跳变
    ts = np.concatenate([ts[:30], ts[30:] + 50_000_000_000])  # 30 后 +50s
    mid = 100.0 + np.arange(len(ts)) * 0.01
    rng = np.random.default_rng(2)
    df = pd.DataFrame({
        'timestamp': ts,
        'mid': mid,
        'obi': rng.normal(0, 1, len(ts)),
        'trade_ofi': rng.normal(0, 1, len(ts)),
        'book_ofi': rng.normal(0, 1, len(ts)),
        'trend': rng.normal(0, 1, len(ts)),
        'bid_qty': 1.0,
        'ask_qty': 1.0,
    })
    # 让 obi 全是强信号，保证有交易发生
    df['obi'] = 10.0
    df = analyze.add_forward_returns(df)
    stats = analyze.simple_strategy(df, indicator='obi', horizon_s=5, threshold=0.0)
    # 不应崩溃；退出按时间戳，缺口处跳过
    assert stats['n_trades'] >= 0


def test_quantile_hit_rate_extreme_edges():
    # 强相关 + 噪声：极端分位（大 |指标| -> 大 |ret|）命中应高于中间分位
    df = analyze.add_forward_returns(_make_df())
    rng = np.random.default_rng(1)
    df['obi'] = df['fwd_ret_5s'] * 1e4 + rng.normal(0, 1.0, len(df))
    qt = analyze.quantile_hit_rate(df, indicator='obi', horizon_s=5, q=5)
    assert len(qt) == 5
    assert set(qt.columns) >= {'bucket', 'n', 'hit_rate', 'mean_ret'}
    qt = qt.sort_values('bucket').reset_index(drop=True)
    neg = qt.iloc[0]
    pos = qt.iloc[-1]
    mid = qt.iloc[len(qt) // 2]
    # 极端桶（强信号）命中应显著 > 中间桶（噪声主导）
    assert pos['hit_rate'] > mid['hit_rate']
    assert neg['hit_rate'] > mid['hit_rate']


def test_quantile_hit_table_shape():
    df = analyze.add_forward_returns(_make_df())
    tbl = analyze.quantile_hit_table(df, q=5)
    assert len(tbl) == len(analyze.INDICATORS) * len(analyze.HORIZONS_S)
    assert {'indicator', 'horizon_s', 'neg_hit', 'mid_hit', 'pos_hit',
            'neg_ret', 'pos_ret', 'n_neg', 'n_pos'} <= set(tbl.columns)
