import numpy as np
from numba import njit

from hftbacktest import BacktestAsset, HashMapMarketDepthBacktest
from hftbacktest.types import BUY_EVENT, SELL_EVENT

from research import config

OUT_COLS = [
    'timestamp', 'mid', 'obi', 'trade_ofi', 'book_ofi', 'trend', 'bid_qty', 'ask_qty'
]


def build_asset(feed, snapshot=None, tick_size=0.1, lot_size=0.001):
    asset = BacktestAsset()
    if isinstance(feed, list):
        asset = asset.data(feed)
    else:
        asset = asset.data([feed])
    if isinstance(snapshot, list):
        if snapshot:
            asset = asset.initial_snapshot(snapshot[0])
    elif snapshot is not None:
        asset = asset.initial_snapshot(snapshot)
    asset = (
        asset
        .tick_size(tick_size)
        .lot_size(lot_size)
        .last_trades_capacity(config.LAST_TRADES_CAP)
    )
    return asset


def build_hbt(feed, snapshot=None, tick_size=0.1, lot_size=0.001):
    return HashMapMarketDepthBacktest(
        [build_asset(feed, snapshot, tick_size, lot_size)]
    )


@njit
def _extract_top(snapshot, is_bid, max_levels, out_px, out_qty):
    """从 depth.snapshot() 流式提取前 max_levels 档（按价格排序），不越界。

    out_px[0:count] 始终保持有序：bid 按价格降序，ask 按价格升序。
    只写入下标 0..max_levels-1，永远不会越界。
    """
    count = 0
    for i in range(len(snapshot)):
        ev = snapshot[i]
        if is_bid:
            if (ev.ev & BUY_EVENT) == 0:
                continue
            # bid：价格越高越靠前
        else:
            if (ev.ev & SELL_EVENT) == 0:
                continue
            # ask：价格越低越靠前

        if count == max_levels:
            # 数组已满：只有优于最差档（或与其同价）才插入并剔除最差档
            worst = out_px[max_levels - 1]
            if is_bid:
                better = ev.px > worst
            else:
                better = ev.px < worst
            if not better and not abs(ev.px - worst) < 1e-12:
                continue
            # 从最差档位置向左找插入点
            pos = max_levels - 1
            while pos > 0:
                if is_bid:
                    if not (ev.px > out_px[pos - 1]):
                        break
                else:
                    if not (ev.px < out_px[pos - 1]):
                        break
                pos -= 1
            # 右移并覆盖最差档（下标不超过 max_levels-1）
            for j in range(max_levels - 1, pos, -1):
                out_px[j] = out_px[j - 1]
                out_qty[j] = out_qty[j - 1]
            out_px[pos] = ev.px
            out_qty[pos] = ev.qty
        else:
            # 数组未满：直接插入并保持有序
            pos = count
            while pos > 0:
                if is_bid:
                    if not (ev.px > out_px[pos - 1]):
                        break
                else:
                    if not (ev.px < out_px[pos - 1]):
                        break
                pos -= 1
            for j in range(count, pos, -1):
                out_px[j] = out_px[j - 1]
                out_qty[j] = out_qty[j - 1]
            out_px[pos] = ev.px
            out_qty[pos] = ev.qty
            count += 1
    return count


@njit
def _level_delta(cur_px, cur_qty, cur_n, prev_px, prev_qty, prev_n):
    """同一价格档位上的数量差分累计（新出现 +cur，消失 -prev，同价 diff）。"""
    total = 0.0
    for i in range(cur_n):
        p = cur_px[i]
        q = cur_qty[i]
        found = False
        for j in range(prev_n):
            if abs(prev_px[j] - p) < 1e-12:
                total += q - prev_qty[j]
                found = True
                break
        if not found:
            total += q
    for j in range(prev_n):
        present = False
        for i in range(cur_n):
            if abs(cur_px[i] - prev_px[j]) < 1e-12:
                present = True
                break
        if not present:
            total -= prev_qty[j]
    return total


@njit
def _sample(hbt, max_rows,
            bid_px_buf, bid_qty_buf, ask_px_buf, ask_qty_buf,
            prev_bid_px, prev_bid_qty, prev_ask_px, prev_ask_qty,
            mid_history,
            out_ts, out_mid, out_obi, out_tofi, out_book_ofi, out_trend,
            out_bid_qty, out_ask_qty):
    n = 0
    depth = hbt.depth(0)
    max_levels = config.BOOK_OFI_LEVELS
    prev_bid_n = 0
    prev_ask_n = 0
    hist_idx = 0
    hist_count = 0
    trend_slots = int(config.TREND_WINDOW_MS / config.SAMPLE_INTERVAL_MS)
    have_prev = False

    # 初始化游标到首个事件时间戳，并对齐到 SAMPLE_INTERVAL_MS 网格，
    # 避免数据起点偏移导致采样时间戳错位。
    if hbt.elapse(0) != 0:
        return n
    interval = config.SAMPLE_INTERVAL_MS
    target = ((hbt.current_timestamp + interval - 1) // interval) * interval
    if hbt.elapse(target - hbt.current_timestamp) != 0:
        return n

    while True:
        ts = hbt.current_timestamp

        bid = depth.best_bid
        ask = depth.best_ask
        bid_qty = depth.best_bid_qty
        ask_qty = depth.best_ask_qty

        mid = (bid + ask) / 2.0
        obi = (bid_qty - ask_qty) / (bid_qty + ask_qty) if (bid_qty + ask_qty) > 0 else np.nan

        # tradeOFI: 本秒成交聚合
        trades = hbt.last_trades(0)
        buy_vol = 0.0
        sell_vol = 0.0
        for i in range(len(trades)):
            ev = trades[i]
            if ev.ev & BUY_EVENT:
                buy_vol += ev.qty
            elif ev.ev & SELL_EVENT:
                sell_vol += ev.qty
        hbt.clear_last_trades(0)
        tofi = (buy_vol - sell_vol) / (buy_vol + sell_vol) if (buy_vol + sell_vol) > 0 else np.nan

        # bookOFI: snapshot 前 N 档差分
        snap = depth.snapshot()
        cur_bid_n = _extract_top(snap, True, max_levels, bid_px_buf, bid_qty_buf)
        cur_ask_n = _extract_top(snap, False, max_levels, ask_px_buf, ask_qty_buf)
        # Rust 端 snapshot() 分配的内存必须手动释放，否则每秒泄漏 ~0.65MB
        depth.snapshot_free(snap)
        if have_prev:
            db = _level_delta(bid_px_buf, bid_qty_buf, cur_bid_n, prev_bid_px, prev_bid_qty, prev_bid_n)
            da = _level_delta(ask_px_buf, ask_qty_buf, cur_ask_n, prev_ask_px, prev_ask_qty, prev_ask_n)
            book_ofi = db - da
        else:
            book_ofi = np.nan
        for i in range(cur_bid_n):
            prev_bid_px[i] = bid_px_buf[i]
            prev_bid_qty[i] = bid_qty_buf[i]
        for i in range(cur_ask_n):
            prev_ask_px[i] = ask_px_buf[i]
            prev_ask_qty[i] = ask_qty_buf[i]
        prev_bid_n = cur_bid_n
        prev_ask_n = cur_ask_n
        have_prev = True

        # trend: 60s 前 mid
        if hist_count >= trend_slots:
            # 读取环形缓冲区中最旧的值（即 trend_slots 个采样前的 mid），
            # 该槽位马上就要被覆盖。
            past_idx = (hist_idx + trend_slots) % trend_slots
            past = mid_history[past_idx]
            trend = (mid - past) / past if past > 0 else np.nan
        else:
            trend = np.nan
        mid_history[hist_idx] = mid
        hist_count += 1
        hist_idx = (hist_idx + 1) % trend_slots

        out_ts[n] = ts
        out_mid[n] = mid
        out_obi[n] = obi
        out_tofi[n] = tofi
        out_book_ofi[n] = book_ofi
        out_trend[n] = trend
        out_bid_qty[n] = bid_qty
        out_ask_qty[n] = ask_qty
        n += 1
        if n >= max_rows:
            break
        if hbt.elapse(interval) != 0:
            break
    return n


def replay_to_df(hbt):
    max_rows = 1_000_000
    bid_px_buf = np.empty(config.BOOK_OFI_LEVELS, np.float64)
    bid_qty_buf = np.empty(config.BOOK_OFI_LEVELS, np.float64)
    ask_px_buf = np.empty(config.BOOK_OFI_LEVELS, np.float64)
    ask_qty_buf = np.empty(config.BOOK_OFI_LEVELS, np.float64)
    prev_bid_px = np.empty(config.BOOK_OFI_LEVELS, np.float64)
    prev_bid_qty = np.empty(config.BOOK_OFI_LEVELS, np.float64)
    prev_ask_px = np.empty(config.BOOK_OFI_LEVELS, np.float64)
    prev_ask_qty = np.empty(config.BOOK_OFI_LEVELS, np.float64)
    trend_slots = int(config.TREND_WINDOW_MS / config.SAMPLE_INTERVAL_MS)
    mid_history = np.zeros(trend_slots, np.float64)

    out_ts = np.empty(max_rows, np.int64)
    out_mid = np.empty(max_rows, np.float64)
    out_obi = np.empty(max_rows, np.float64)
    out_tofi = np.empty(max_rows, np.float64)
    out_book_ofi = np.empty(max_rows, np.float64)
    out_trend = np.empty(max_rows, np.float64)
    out_bid_qty = np.empty(max_rows, np.float64)
    out_ask_qty = np.empty(max_rows, np.float64)

    n = _sample(
        hbt, max_rows,
        bid_px_buf, bid_qty_buf, ask_px_buf, ask_qty_buf,
        prev_bid_px, prev_bid_qty, prev_ask_px, prev_ask_qty,
        mid_history,
        out_ts, out_mid, out_obi, out_tofi, out_book_ofi, out_trend,
        out_bid_qty, out_ask_qty,
    )

    import pandas as pd
    df = pd.DataFrame({
        'timestamp': out_ts[:n],
        'mid': out_mid[:n],
        'obi': out_obi[:n],
        'trade_ofi': out_tofi[:n],
        'book_ofi': out_book_ofi[:n],
        'trend': out_trend[:n],
        'bid_qty': out_bid_qty[:n],
        'ask_qty': out_ask_qty[:n],
    })
    return df
