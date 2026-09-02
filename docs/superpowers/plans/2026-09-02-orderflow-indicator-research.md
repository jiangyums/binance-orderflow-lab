# 订单流指标预测力研究（阶段 A）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `binance-orderflow-lab` 独立仓库中实现研究阶段（阶段 A）：从 data.binance.vision 下载历史数据 → 转 hftbacktest npz → 用 hftbacktest Backtest 引擎回放 → 每秒采样 OBI/tradeOFI/bookOFI/60s 趋势 → 命中率/分位数/简单开平仓统计 → 生成报告。

**Architecture:** 纯 Python + hftbacktest pyo3 绑定。数据准备用 `hftbacktest.data.utils.binancehistmktdata`（已存在于安装的 hftbacktest 包）转 npz；回放采样用 `@njit` 函数驱动 `HashMapMarketDepthBacktest`（`elapse` 按 1s 步进），输出固定 schema 秒级 DataFrame；统计分析用 pandas/numpy/scipy；报告用 markdown + matplotlib。

**Tech Stack:** Python 3.11+、numpy、pandas、scipy、matplotlib、requests、hftbacktest（pyo3 绑定）、numba（hftbacktest 依赖自带）

---

## 前置：关键事实（已确认）

- `elapse(duration)` 返回码：`0=Ok`，`1=EndOfData`（`py-hftbacktest/src/backtest.rs:15-20`）。
- data.binance.vision 的 depth/trades CSV 时间戳单位为**毫秒**（`binancehistmktdata.convert` 中 `exch_ts = int(row[timestamp_col])`）。因此采样间隔为 `1000`（1s in ms）。
- `binancehistmktdata.convert(depth_filename, trades_filename, output_filename)`：
  - depth 文件列：`symbol,timestamp,trans_id,first_update_id,last_update_id,side,update_type,price,qty`（side 为 `b`/`a`）
  - trades 文件列：`id,price,qty,quote_qty,time,is_buyer_maker`
  - 输出 npz，键 `data`。
- `binancehistmktdata.convert_snapshot(snapshot_filename, output_filename)`：bookDepth 快照转初始快照 npz。
- hftbacktest Python 接口（`py-hftbacktest/hftbacktest/__init__.py`）：
  - `BacktestAsset().data([...]).initial_snapshot(...).tick_size(...).lot_size(...).last_trades_capacity(...)`
  - `HashMapMarketDepthBacktest([asset])` 返回可在 `@njit` 中使用的绑定对象。
  - `hbt.depth(0)`：`.best_bid/.best_ask/.best_bid_qty/.best_ask_qty/.snapshot()`。
  - `hbt.last_trades(0)`：`EVENT_ARRAY`（`event_dtype`：`ev/exch_ts/local_ts/px/qty/order_id/ival/fval`）。
  - `hbt.clear_last_trades(asset_no)`、`hbt.current_timestamp`。
  - 事件位标志：`BUY_EVENT=1<<29`，`SELL_EVENT=1<<28`（`hftbacktest/types.py`）。
- 环境：仓库 venv 为 `.HftBacktest/Scripts/python.exe`（Python 3.11.9），**当前缺 numpy/pandas 等依赖**，需安装。
- 阶段 A 不需要下单/撮合，latency/queue/fee 模型使用 BacktestAsset 默认占位即可。

---

### Task 1: 环境准备

**Files:**
- Modify: `C:\workplace\binance-orderflow-lab\.gitignore`（确认 `data/` 已忽略；如无 `results/` 加入）
- Create: `C:\workplace\binance-orderflow-lab\research\__init__.py`

- [ ] **Step 1: 安装研究依赖到仓库 venv**

```powershell
& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m pip install --upgrade pip
& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m pip install numpy pandas scipy matplotlib requests hftbacktest
```

- [ ] **Step 2: 验证 hftbacktest 与数据工具可用**

```powershell
& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -c "import hftbacktest, numpy, pandas; from hftbacktest.data.utils import binancehistmktdata; print('OK', hftbacktest.__version__ if hasattr(hftbacktest,'__version__') else '')"
```

Expected: 打印 `OK` 无 ImportError。

- [ ] **Step 3: 创建 `research/__init__.py` 与 `.gitignore` 补充**

`.gitignore` 追加（如 `results/` 未在忽略列表）：
```
research/results/
data/
```

创建 `research/__init__.py`：
```python
"""Order-flow indicator research (Phase A)."""
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore research/__init__.py
git commit -m "chore(research): set up phase A environment"
```

---

### Task 2: 配置模块

**Files:**
- Create: `C:\workplace\binance-orderflow-lab\research\config.py`
- Test: `C:\workplace\binance-orderflow-lab\research\tests\test_config.py`

- [ ] **Step 1: 写失败测试**

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research import config


def test_config_values():
    assert config.SYMBOL.upper() == 'BTCUSDT'
    assert config.SAMPLE_INTERVAL_MS == 1000
    assert config.TREND_WINDOW_MS == 60_000
    assert config.FUTURE_HORIZONS_S == [5, 15, 60]
    assert config.TAKER_FEE == 0.0005
    assert config.BOOK_OFI_LEVELS == 20
```

- [ ] **Step 2: 运行确认失败**

Run: `& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m pytest research/tests/test_config.py -v`
Expected: `ModuleNotFoundError: No module named 'research.config'`（`config.py` 尚不存在）或 ImportError。

- [ ] **Step 3: 实现 `research/config.py`**

```python
SYMBOL = 'btcusdt'

# data.binance.vision 时间戳单位 = 毫秒
SAMPLE_INTERVAL_MS = 1000      # 1s 采样
TREND_WINDOW_MS = 60_000       # 60s 趋势窗口

FUTURE_HORIZONS_S = [5, 15, 60]
HORIZONS_MS = [h * 1000 for h in FUTURE_HORIZONS_S]

BOOK_OFI_LEVELS = 20           # bookOFI 前 N 档（等权）
LAST_TRADES_CAP = 10_000

# 交易成本
TAKER_FEE = 0.0005             # 单边 0.05%
ROUND_TRIP_COST = 2 * TAKER_FEE

# 简单策略参数
Z_WINDOW_S = 300               # Z-score 滚动窗口
Z_THRESHOLD = 1.5

# 数据
DATA_DIR = 'data'
RESULTS_DIR = 'research/results'
CACHE_DIR = 'data/hist'

# 默认研究日期范围（近 1 周）
START_DATE = '2026-08-26'
END_DATE = '2026-09-01'
```

- [ ] **Step 4: 运行确认通过**

Run: `& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m pytest research/tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add research/config.py research/tests/test_config.py
git commit -m "feat(research): add config module"
```

---

### Task 3: 数据准备（下载 + 转 npz）

**Files:**
- Create: `C:\workplace\binance-orderflow-lab\research\prepare_data.py`
- Test: `C:\workplace\binance-orderflow-lab\research\tests\test_prepare_data.py`

- [ ] **Step 1: 写失败测试（快照转换，纯函数，无网络）**

```python
import sys
import os
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hftbacktest.data.utils import binancehistmktdata
from research import prepare_data


def test_convert_hist_depth_trades_roundtrip():
    # 构造 data.binance.vision 格式的 depth CSV 与 aggTrades CSV
    depth_csv = (
        'symbol,timestamp,trans_id,first_update_id,last_update_id,side,update_type,price,qty\n'
        'BTCUSDT,1660000000000,1,100,200,b,0,24670.90,2.5\n'
        'BTCUSDT,1660000000000,2,201,300,a,0,24671.00,1.5\n'
    )
    trades_csv = (
        'id,price,qty,quote_qty,time,is_buyer_maker\n'
        '1,24670.90,0.5,12335.45,1660000000000,false\n'
        '2,24671.00,0.3,7401.30,1660000001000,true\n'
    )
    with tempfile.TemporaryDirectory() as td:
        d = os.path.join(td, 'depth.csv')
        t = os.path.join(td, 'trades.csv')
        out = os.path.join(td, 'out.npz')
        with open(d, 'w') as f:
            f.write(depth_csv)
        with open(t, 'w') as f:
            f.write(trades_csv)
        arr = binancehistmktdata.convert(d, t, out)
        assert len(arr) == 4
        loaded = np.load(out)['data']
        assert len(loaded) == 4
        assert (loaded['ev'] & 2).any()   # TRADE_EVENT present
        assert (loaded['ev'] & 1).any()   # DEPTH_EVENT present
        # depth side: b -> BUY_EVENT, a -> SELL_EVENT
        assert (loaded['ev'] & (1 << 29)).any()
        assert (loaded['ev'] & (1 << 28)).any()


def test_download_url_template():
    url = prepare_data.hist_data_url('aggTrades', '2026-08-26')
    assert url == (
        'https://data.binance.vision/data/futures/um/daily/BTCUSDT/aggTrades/'
        'BTCUSDT-aggTrades-2026-08-26.zip'
    )
```

- [ ] **Step 2: 运行确认失败**

Run: `& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m pytest research/tests/test_prepare_data.py -v`
Expected: FAIL（`prepare_data` 不存在）。

- [ ] **Step 3: 实现 `research/prepare_data.py`**

```python
import gzip
import os
import shutil
import zipfile
from typing import Optional

import requests

from research import config

BASE_URL = 'https://data.binance.vision/data/futures/um/daily'
DEPTH_LEVEL = 1000


def hist_data_url(book_type: str, date: str) -> str:
    sym = config.SYMBOL.upper()
    fname = f'{sym}-{book_type}-{date}.zip'
    if book_type == 'bookDepth':
        fname = f'{sym}-{book_type}-{DEPTH_LEVEL}-{date}.zip'
    return f'{BASE_URL}/{sym}/{book_type}/{fname}'


def download_zip(url: str, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    fname = os.path.basename(url)
    dest = os.path.join(dest_dir, fname)
    if os.path.exists(dest):
        return dest
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    with open(dest, 'wb') as f:
        f.write(resp.content)
    return dest


def _read_zip_text(path: str) -> str:
    with zipfile.ZipFile(path) as zf:
        name = zf.namelist()[0]
        with zf.open(name) as f:
            raw = f.read()
    if path.endswith('.gz') or name.endswith('.gz'):
        raw = gzip.decompress(raw)
    return raw.decode('utf-8')


def prepare_day(date: str, data_dir: str = config.DATA_DIR) -> dict:
    cache = os.path.join(data_dir, 'hist', date)
    os.makedirs(cache, exist_ok=True)

    agg = download_zip(hist_data_url('aggTrades', date), cache)
    depth = download_zip(hist_data_url('depth', date), cache)
    try:
        bookdepth = download_zip(hist_data_url('bookDepth', date), cache)
        bookdepth_ok = True
    except Exception:
        bookdepth = None
        bookdepth_ok = False

    trades_txt = os.path.join(cache, 'trades.csv')
    depth_txt = os.path.join(cache, 'depth.csv')
    snap_txt = os.path.join(cache, 'snapshot.csv')

    with open(trades_txt, 'w', newline='') as f:
        f.write(_read_zip_text(agg))
    with open(depth_txt, 'w', newline='') as f:
        f.write(_read_zip_text(depth))

    from hftbacktest.data.utils import binancehistmktdata

    feed_npz = os.path.join(cache, 'feed.npz')
    binancehistmktdata.convert(depth_txt, trades_txt, feed_npz, buffer_size=200_000_000)

    result = {'feed': feed_npz, 'snapshot': None}
    if bookdepth_ok:
        with open(snap_txt, 'w', newline='') as f:
            f.write(_read_zip_text(bookdepth))
        snap_npz = os.path.join(cache, 'snapshot.npz')
        binancehistmktdata.convert_snapshot(snap_txt, snap_npz)
        result['snapshot'] = snap_npz
    return result


def prepare_range(start: str, end: str, data_dir: str = config.DATA_DIR) -> list:
    from datetime import date, timedelta

    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    out = []
    d = s
    while d <= e:
        iso = d.isoformat()
        try:
            out.append(prepare_day(iso, data_dir))
        except Exception as exc:
            print(f'[prepare] {iso} skipped: {type(exc).__name__}: {exc}')
        d += timedelta(days=1)
    return out
```

- [ ] **Step 4: 运行确认通过**

Run: `& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m pytest research/tests/test_prepare_data.py -v`
Expected: PASS（两个测试均不触网）。

- [ ] **Step 5: 真数据冒烟（可选，网络允许时）**

Run: `& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -c "from research.prepare_data import prepare_day; print(prepare_day('2026-08-26'))"`
Expected: 打印含 `feed` 路径的 dict。若网络受限，此步跳过并记录。

- [ ] **Step 6: Commit**

```bash
git add research/prepare_data.py research/tests/test_prepare_data.py
git commit -m "feat(research): add historical data download and npz conversion"
```

---

### Task 4: 回放采样（hftbacktest 引擎 + 每秒四指标）

**Files:**
- Create: `C:\workplace\binance-orderflow-lab\research\replay_indicators.py`
- Test: `C:\workplace\binance-orderflow-lab\research\tests\test_replay_indicators.py`

**设计：**
- `build_asset(feed_npz, snapshot_npz=None, tick_size=0.1, lot_size=0.001)` → `BacktestAsset`
- `sample_indicators(hbt, max_rows)`（`@njit`）→ 预分配数组输出，逐秒：
  - `elapse(config.SAMPLE_INTERVAL_MS)`，返回非 0 即停。
  - mid、OBI（best bid/ask qty）、tradeOFI（`last_trades` 聚合，清空）、bookOFI（`depth.snapshot()` 前 20 档与上一帧差分）、trend（60s 前 mid）。
- `replay_to_df(feed_npz, snapshot_npz)` → pandas DataFrame，schema 固定：`timestamp, mid, obi, trade_ofi, book_ofi, trend, bid_qty, ask_qty`。

- [ ] **Step 1: 写失败测试（合成数据，无网络）**

```python
import sys
import os

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hftbacktest import BacktestAsset, HashMapMarketDepthBacktest
from hftbacktest.types import (
    DEPTH_EVENT, DEPTH_SNAPSHOT_EVENT, LOCAL_EVENT, BUY_EVENT, SELL_EVENT,
    TRADE_EVENT, event_dtype,
)

from research import config
from research.replay_indicators import build_asset, replay_to_df


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
```

- [ ] **Step 2: 运行确认失败**

Run: `& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m pytest research/tests/test_replay_indicators.py -v`
Expected: FAIL（模块不存在）。

- [ ] **Step 3: 实现 `research/replay_indicators.py`**

```python
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
    if snapshot is not None:
        if isinstance(snapshot, list):
            asset = asset.initial_snapshot(snapshot[0])
        else:
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
    """从 depth.snapshot() 提取前 max_levels 档（按价格排序）。"""
    count = 0
    for i in range(len(snapshot)):
        ev = snapshot[i]
        if is_bid:
            if (ev.ev & BUY_EVENT) == 0:
                continue
        else:
            if (ev.ev & SELL_EVENT) == 0:
                continue
        out_px[count] = ev.px
        out_qty[count] = ev.qty
        count += 1
    # 冒泡：bid 降序 / ask 升序，仅保留前 max_levels
    for i in range(min(count, max_levels)):
        for j in range(i + 1, count):
            if is_bid:
                swap = out_px[j] > out_px[i]
            else:
                swap = out_px[j] < out_px[i]
            if swap:
                out_px[i], out_px[j] = out_px[j], out_px[i]
                out_qty[i], out_qty[j] = out_qty[j], out_qty[i]
    return min(count, max_levels)


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

    while True:
        res = hbt.elapse(config.SAMPLE_INTERVAL_MS)
        if res != 0:
            break
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
        mid_history[hist_idx] = mid
        hist_count += 1
        if hist_count > trend_slots:
            past = mid_history[(hist_idx + 1) % trend_slots]
            trend = (mid - past) / past if past > 0 else np.nan
        else:
            trend = np.nan
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
```

> 注：`_sample` 中 `hbt.depth(0)` 返回绑定对象在 njit 中可访问属性（`example.py` 已证）。若 `snapshot()`/`last_trades()` 在 njit 报类型错误，将这两个辅助循环移到 `_sample` 内部直接内联（见 Step 4 排错提示）。

- [ ] **Step 4: 运行确认通过**

Run: `& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m pytest research/tests/test_replay_indicators.py -v`
Expected: PASS。

排错提示：
- 若 numba 无法编译 `depth.snapshot()` 或 `hbt.last_trades(0)`，将 `snap = depth.snapshot()` 与 `trades = hbt.last_trades(0)` 改为直接内联访问，并确保在 `@njit` 外传入 `config.BOOK_OFI_LEVELS` 等常量（numba 需要编译期常量，通过函数默认参数或 `Literal` 处理；上述代码将常量从模块直接读取，numba 可解析）。

- [ ] **Step 5: Commit**

```bash
git add research/replay_indicators.py research/tests/test_replay_indicators.py
git commit -m "feat(research): add hftbacktest replay sampling of four indicators"
```

---

### Task 5: 统计分析（命中率 / 分位数 / 简单策略）

**Files:**
- Create: `C:\workplace\binance-orderflow-lab\research\analyze.py`
- Test: `C:\workplace\binance-orderflow-lab\research\tests\test_analyze.py`

- [ ] **Step 1: 写失败测试**

```python
import sys
import os

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    # 随机游走 + 随机指标：命中率应接近 50%（容忍度放宽，仅验证接口）
    assert 0.0 <= hr['hit_rate'] <= 1.0
    assert 'n' in hr and 'p_value' in hr


def test_simple_strategy_returns_stats():
    df = analyze.add_forward_returns(_make_df())
    stats = analyze.simple_strategy(df, indicator='obi', horizon_s=5)
    for key in ['n_trades', 'win_rate', 'cum_profit', 'max_drawdown', 'sharpe']:
        assert key in stats
```

- [ ] **Step 2: 运行确认失败**

Run: `& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m pytest research/tests/test_analyze.py -v`
Expected: FAIL。

- [ ] **Step 3: 实现 `research/analyze.py`**

```python
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


def _drop_small_abs(df, indicator, frac=0.10):
    threshold = df[indicator].abs().quantile(frac)
    return df[df[indicator].abs() >= threshold]


def hit_rate(df, indicator, horizon_s):
    sub = _drop_small_abs(df.dropna(subset=[indicator, f'fwd_ret_{horizon_s}s']), indicator)
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
    sharpe = t['net_ret'].mean() / t['net_ret'].std() * np.sqrt(86400 / horizon_s) if t['net_ret'].std() > 0 else np.nan
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
```

- [ ] **Step 4: 运行确认通过**

Run: `& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m pytest research/tests/test_analyze.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add research/analyze.py research/tests/test_analyze.py
git commit -m "feat(research): add hit-rate, quantile, and simple strategy analysis"
```

---

### Task 6: 报告输出与主入口

**Files:**
- Create: `C:\workplace\binance-orderflow-lab\research\report.py`
- Create: `C:\workplace\binance-orderflow-lab\research\run.py`
- Test: `C:\workplace\binance-orderflow-lab\research\tests\test_report.py`

- [ ] **Step 1: 写失败测试**

```python
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research import report


def test_render_markdown_contains_tables():
    import pandas as pd
    ht = pd.DataFrame({'indicator': ['obi'], 'horizon_s': [5],
                       'hit_rate': [0.6], 'n': [100], 'p_value': [0.02]})
    st = pd.DataFrame({'indicator': ['obi'], 'horizon_s': [5], 'n_trades': [10],
                       'win_rate': [0.5], 'cum_profit': [0.01],
                       'max_drawdown': [-0.02], 'sharpe': [1.2]})
    md = report.render_markdown(ht, st)
    assert '# 订单流指标预测力研究报告' in md
    assert '命中率' in md and '简单策略' in md


def test_save_report_writes_file():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, 'report.md')
        report.save_report('content', path)
        assert os.path.exists(path)
        with open(path, encoding='utf-8') as f:
            assert f.read() == 'content'
```

- [ ] **Step 2: 运行确认失败**

Run: `& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m pytest research/tests/test_report.py -v`
Expected: FAIL。

- [ ] **Step 3: 实现 `research/report.py`**

```python
import os

import pandas as pd


def render_markdown(hit_rate_df: pd.DataFrame, strategy_df: pd.DataFrame) -> str:
    lines = []
    lines.append('# 订单流指标预测力研究报告')
    lines.append('')
    lines.append('## 方向命中率')
    lines.append('')
    if len(hit_rate_df):
        t = hit_rate_df.copy()
        t['显著'] = t['p_value'] < 0.05
        lines.append(t.to_markdown(index=False))
    else:
        lines.append('（无样本）')
    lines.append('')
    lines.append('## 简单开平仓策略（taker 0.05% 双边）')
    lines.append('')
    if len(strategy_df):
        lines.append(strategy_df.to_markdown(index=False))
    else:
        lines.append('（无交易）')
    lines.append('')
    return '\n'.join(lines)


def save_report(content: str, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
```

- [ ] **Step 4: 实现 `research/run.py`**

```python
import argparse
import os

from research import analyze, config, prepare_data, report
from research.replay_indicators import build_hbt, replay_to_df


def main():
    parser = argparse.ArgumentParser(description='Order-flow indicator research')
    parser.add_argument('--start', default=config.START_DATE)
    parser.add_argument('--end', default=config.END_DATE)
    parser.add_argument('--no-download', action='store_true',
                        help='跳过下载，使用已有缓存')
    args = parser.parse_args()

    if args.no_download:
        days = [{'feed': os.path.join(config.DATA_DIR, 'hist', d, 'feed.npz'),
                 'snapshot': os.path.join(config.DATA_DIR, 'hist', d, 'snapshot.npz')}
                for d in _date_list(args.start, args.end)
                if os.path.exists(os.path.join(config.DATA_DIR, 'hist', d, 'feed.npz'))]
    else:
        days = prepare_data.prepare_range(args.start, args.end)

    feeds = [d['feed'] for d in days if os.path.exists(d['feed'])]
    snapshots = [d['snapshot'] for d in days if d['snapshot'] and os.path.exists(d['snapshot'])]

    hbt = build_hbt(feeds, snapshots)
    df = replay_to_df(hbt)
    df = analyze.add_forward_returns(df)

    ht = analyze.hit_rate_table(df)
    st = analyze.strategy_table(df)

    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    ht.to_csv(os.path.join(config.RESULTS_DIR, 'hit_rate.csv'), index=False)
    st.to_csv(os.path.join(config.RESULTS_DIR, 'strategy.csv'), index=False)
    df.to_csv(os.path.join(config.RESULTS_DIR, 'indicators.csv'), index=False)

    md = report.render_markdown(ht, st)
    report.save_report(md, os.path.join(config.RESULTS_DIR, 'report.md'))
    print(md)


def _date_list(start, end):
    from datetime import date, timedelta
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    out = []
    d = s
    while d <= e:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


if __name__ == '__main__':
    main()
```

- [ ] **Step 5: 运行测试确认通过**

Run: `& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m pytest research/tests/ -v`
Expected: 全部 PASS。

- [ ] **Step 6: Commit**

```bash
git add research/report.py research/run.py research/tests/test_report.py
git commit -m "feat(research): add report rendering and run entrypoint"
```

---

### Task 7: 真数据端到端运行与报告生成

**Files:**
- Modify: `C:\workplace\binance-orderflow-lab\research\run.py`（如需微调）

- [ ] **Step 1: 先验证单日数据可用（网络允许时）**

```powershell
& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -c "from research.prepare_data import prepare_day; r=prepare_day('2026-08-26'); print(r)"
```
Expected: 打印 feed/snapshot 路径。若网络受限，跳过本步并告知用户需在有网环境运行。

- [ ] **Step 2: 运行完整研究流程**

```powershell
& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m research.run --start 2026-08-26 --end 2026-09-01
```
Expected: 生成 `research/results/report.md`、`hit_rate.csv`、`strategy.csv`、`indicators.csv`。

- [ ] **Step 3: 检查输出数值合理性**

Run: `& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -c "import pandas as pd; ht=pd.read_csv('research/results/hit_rate.csv'); print(ht.describe())"`
Expected: 命中率在 0–1 之间，样本数>0。

- [ ] **Step 4: Commit 结果与报告**

```bash
git add research/results
git commit -m "feat(research): phase A results for first week"
```

---

## 自审记录

- **Spec 覆盖**：spec §5 数据管线 → Task 3；§6 四指标 → Task 4；§7 三类统计 → Task 5；§9 测试 → Task 2/3/4/5 测试；§10 输出 → Task 6/7。阶段 B（Rust）不在本计划内，属后续独立计划（spec §3 已分阶段）。
- **占位符**：无 TBD/TODO；所有步骤含完整代码。
- **类型一致性**：`replay_to_df` 输出列名与 `analyze.add_forward_returns`/`hit_rate`/`simple_strategy` 使用的 `indicator` 名（`obi/trade_ofi/book_ofi/trend`）一致；`OUT_COLS` 与测试断言一致。`HORIZONS_S` 在 analyze 中重导出。
- **已知风险**：`_sample` 中 numba 对 `hbt.depth(0)` 返回绑定对象的 `snapshot()`/`last_trades()` 的编译兼容性需在 Task 4 Step 4 验证；已在步骤中给出排错路径。
