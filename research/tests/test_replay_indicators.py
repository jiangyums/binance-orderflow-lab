import numpy as np

from hftbacktest import BacktestAsset, HashMapMarketDepthBacktest
from hftbacktest.types import (
    DEPTH_EVENT, DEPTH_SNAPSHOT_EVENT, LOCAL_EVENT, BUY_EVENT, SELL_EVENT,
    TRADE_EVENT, event_dtype,
)

from research import config
from research.replay_indicators import build_asset, replay_to_df

# 数据时间戳单位 = 纳秒（与 binancefutures.convert 输出一致），1s = 1_000_000_000
SEC = 1_000_000_000


def _event(ev, ts, px, qty):
    return (ev, ts, ts, px, qty, 0, 0, 0)


def _make_asset():
    events = []
    ts0 = 1_660_000_000_000_000_000
    # 初始快照：bid 24670.9 x2.5 / ask 24671.0 x1.5
    events.append(_event(DEPTH_SNAPSHOT_EVENT | LOCAL_EVENT | BUY_EVENT, ts0 - 1, 24670.9, 2.5))
    events.append(_event(DEPTH_SNAPSHOT_EVENT | LOCAL_EVENT | SELL_EVENT, ts0 - 1, 24671.0, 1.5))
    # 前几秒深度小幅变动
    for k in range(1, 4):
        t = ts0 + k * SEC
        events.append(_event(DEPTH_EVENT | LOCAL_EVENT | BUY_EVENT, t, 24670.9, 2.5 + 0.1 * k))
        events.append(_event(DEPTH_EVENT | LOCAL_EVENT | SELL_EVENT, t, 24671.0, 1.5 + 0.1 * k))
    # 一笔主动买成交（taker buy）在 ts0+5s
    events.append(_event(TRADE_EVENT | LOCAL_EVENT | BUY_EVENT, ts0 + 5 * SEC, 24670.9, 0.5))
    # 一笔主动卖成交在 ts0+6s
    events.append(_event(TRADE_EVENT | LOCAL_EVENT | SELL_EVENT, ts0 + 6 * SEC, 24671.0, 0.3))
    # 尾部深度事件：保证 6s 网格被采样到（否则最后一个网格会因 EndOfData 跳过）
    events.append(_event(DEPTH_EVENT | LOCAL_EVENT | BUY_EVENT, ts0 + 7 * SEC, 24670.9, 2.8))
    events.append(_event(DEPTH_EVENT | LOCAL_EVENT | SELL_EVENT, ts0 + 7 * SEC, 24671.0, 1.2))

    data = np.array(sorted(events, key=lambda e: e[1]), dtype=event_dtype)
    asset = (
        BacktestAsset()
        .data([data])
        .tick_size(0.1)
        .lot_size(0.001)
        .last_trades_capacity(config.LAST_TRADES_CAP)
    )
    return asset


def test_build_asset_empty_snapshot_list_ok():
    a = build_asset([np.zeros(0, dtype=event_dtype)], [])
    assert a is not None


def test_replay_produces_rows():
    hbt = HashMapMarketDepthBacktest([_make_asset()])
    df = replay_to_df(hbt)
    assert len(df) >= 3
    assert list(df.columns) == [
        'timestamp', 'mid', 'obi', 'trade_ofi', 'book_ofi', 'trend', 'bid_qty', 'ask_qty'
    ]
    # mid 应为 (24670.9 + 24671.0) / 2 = 24670.95
    assert np.isclose(df['mid'].iloc[0], 24670.95)
    # OBI = (2.5 - 1.5) / (2.5 + 1.5) = 0.25
    assert np.isclose(df['obi'].iloc[0], 0.25)


def test_trade_ofi_bucket():
    hbt = HashMapMarketDepthBacktest([_make_asset()])
    df = replay_to_df(hbt)
    # 5s 那一秒出现主动买 0.5 -> trade_ofi=+0.5（绝对净量，非归一化）
    row5 = df[df['timestamp'] == 1_660_000_005_000_000_000]
    assert len(row5) == 1
    assert np.isclose(row5['trade_ofi'].iloc[0], 0.5)
    # 6s 那一秒出现主动卖 0.3 -> trade_ofi=-0.3
    row6 = df[df['timestamp'] == 1_660_000_006_000_000_000]
    assert len(row6) == 1
    assert np.isclose(row6['trade_ofi'].iloc[0], -0.3)


def test_deep_book_does_not_crash():
    events = []
    ts0 = 1_660_000_000_000_000_000
    # 500 bid levels and 500 ask levels in the snapshot
    for i in range(500):
        events.append(_event(DEPTH_SNAPSHOT_EVENT | LOCAL_EVENT | BUY_EVENT, ts0 - 1, 24670.0 - 0.1 * i, 1.0))
        events.append(_event(DEPTH_SNAPSHOT_EVENT | LOCAL_EVENT | SELL_EVENT, ts0 - 1, 24671.0 + 0.1 * i, 1.0))
    # a couple seconds of depth activity so elapse advances
    for k in range(1, 3):
        t = ts0 + k * SEC
        events.append(_event(DEPTH_EVENT | LOCAL_EVENT | BUY_EVENT, t, 24670.0, 1.0 + 0.1))
        events.append(_event(DEPTH_EVENT | LOCAL_EVENT | SELL_EVENT, t, 24671.0, 1.0 - 0.1))
    data = np.array(sorted(events, key=lambda e: e[1]), dtype=event_dtype)
    asset = (BacktestAsset().data([data]).tick_size(0.1).lot_size(0.001).last_trades_capacity(config.LAST_TRADES_CAP))
    hbt = HashMapMarketDepthBacktest([asset])
    df = replay_to_df(hbt)
    assert len(df) >= 2
    assert np.isclose(df['obi'].iloc[0], 0.0)  # symmetric 500/500 -> 0


def test_per_trade_to_df_one_row_per_trade():
    from research.replay_indicators import replay_per_trade_to_df
    hbt = HashMapMarketDepthBacktest([_make_asset()])
    df = replay_per_trade_to_df(hbt)
    # 合成数据含 2 笔成交（5s 买 0.5、6s 卖 0.3）-> 2 行
    assert len(df) == 2
    # 每行 trade_ofi = 单笔 side*qty（事件驱动，非聚合）
    assert np.isclose(df['trade_ofi'].iloc[0], 0.5)
    assert np.isclose(df['trade_ofi'].iloc[1], -0.3)
    # 时间戳为成交时刻
    assert df['timestamp'].iloc[0] == 1_660_000_005_000_000_000
    assert df['timestamp'].iloc[1] == 1_660_000_006_000_000_000
    # mid 为采样时盘口快照
    assert np.isclose(df['mid'].iloc[0], 24670.95)
