import numpy as np

from hftbacktest import BacktestAsset, HashMapMarketDepthBacktest
from hftbacktest.types import (
    DEPTH_EVENT, DEPTH_SNAPSHOT_EVENT, LOCAL_EVENT, BUY_EVENT, SELL_EVENT,
    TRADE_EVENT, event_dtype,
)

from research import config
from research.replay_indicators import replay_to_df


def _event(ev, ts, px, qty):
    return (ev, ts, ts, px, qty, 0, 0, 0)


def _make_asset():
    events = []
    ts0 = 1_660_000_000_000
    # 初始快照：bid 24670.9 x2.5 / ask 24671.0 x1.5
    events.append(_event(DEPTH_SNAPSHOT_EVENT | LOCAL_EVENT | BUY_EVENT, ts0 - 1, 24670.9, 2.5))
    events.append(_event(DEPTH_SNAPSHOT_EVENT | LOCAL_EVENT | SELL_EVENT, ts0 - 1, 24671.0, 1.5))
    # 前几秒深度小幅变动
    for k in range(1, 4):
        t = ts0 + k * 1000
        events.append(_event(DEPTH_EVENT | LOCAL_EVENT | BUY_EVENT, t, 24670.9, 2.5 + 0.1 * k))
        events.append(_event(DEPTH_EVENT | LOCAL_EVENT | SELL_EVENT, t, 24671.0, 1.5 + 0.1 * k))
    # 一笔主动买成交（taker buy）在 ts0+5s
    events.append(_event(TRADE_EVENT | LOCAL_EVENT | BUY_EVENT, ts0 + 5000, 24670.9, 0.5))
    # 一笔主动卖成交在 ts0+6s
    events.append(_event(TRADE_EVENT | LOCAL_EVENT | SELL_EVENT, ts0 + 6000, 24671.0, 0.3))

    data = np.array(sorted(events, key=lambda e: e[1]), dtype=event_dtype)
    asset = (
        BacktestAsset()
        .data([data])
        .tick_size(0.1)
        .lot_size(0.001)
        .last_trades_capacity(config.LAST_TRADES_CAP)
    )
    return asset


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
    # 5s 那一秒出现主动买 0.5 -> trade_ofi=+1.0（仅一笔买）
    row5 = df[df['timestamp'] == 1_660_000_005_000]
    assert len(row5) == 1
    assert np.isclose(row5['trade_ofi'].iloc[0], 1.0)
