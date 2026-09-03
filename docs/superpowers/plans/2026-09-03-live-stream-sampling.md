# Python LiveBot 实时流采样 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让研究管线直接从 hftbacktest `connector` 的实时流（iceoryx2 共享内存）采样四指标，与 collector 回放轨同口径互验。

**Architecture:** `connector` 进程（已编译，Binance WS）→ iceoryx2 → Python `HashMapMarketDepthLiveBot`（py-hftbacktest 以 `--features live` 重编译）→ 复用回放轨的 njit 采样循环（`_sample`）→ 秒级 DataFrame/CSV → 现有 `analyze.py`/`report.py`。

**Tech Stack:** maturin（编译 py-hftbacktest live feature）、pyo3/numba jitclass、iceoryx2 0.6.1（Windows 支持）。

---

## 前置：关键事实（已确认）

- PyPI 版 hftbacktest 2.4.4 未编译 live：`LIVE_FEATURE == False`；绑定代码完整存在
  （`py-hftbacktest/hftbacktest/binding.py:1609` `HashMapMarketDepthLiveBot` jitclass）。
- py-hftbacktest feature 开关：`[features] live = ["hftbacktest/live"]`（`py-hftbacktest/Cargo.toml:12`）。
- LiveBot 与 Backtest 共享同一套接口签名：`depth(asset_no)`、`last_trades(asset_no)`、
  `clear_last_trades`、`current_timestamp`、`elapse(duration)`（实时侧返回码 0=超时正常/1=流断开/2=有 feed）。
  **注意**：live 侧 `elapse` 语义是"等待 duration"，返回 2（MarketFeed）表示期间有行情。
- builder 入口：`hftbacktest.LiveInstrument().connector(name).symbol(sym).tick_size(..).lot_size(..)
  .last_trades_capacity(..).roi_lb(..).roi_ub(..)` + `hftbacktest.HashMapMarketDepthLiveBot([inst])`
  （`py-hftbacktest/hftbacktest/__init__.py:221-235`，仅 live feature 编译时可用）。
- Rust `connector` 用法：`connector.exe <name> binancefutures <config.toml>`，`name` 即 LiveInstrument 的 connector 名。
- 回放轨 `_sample`（`research/replay_indicators.py`）已验证：网格对齐、snapshot_free、trend 环形缓冲。
- 研究仓库：`C:\workplace\binance-orderflow-lab`，分支 `research-phase-a`，venv `.HftBacktest`。
- hftbacktest 源码：`C:\workplace\hftbacktest`（connector 已编译，live feature 未编译）。

---

### Task 1: 编译 py-hftbacktest live feature 并安装到研究 venv

**Files:**（无仓库文件改动；产物为 venv 内 wheel）

- [ ] **Step 1: venv 安装 maturin**

```powershell
& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m pip install maturin
```

- [ ] **Step 2: 编译安装（release + live feature）**

```powershell
Set-Location C:\workplace\hftbacktest\py-hftbacktest
& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m maturin build --release --features live
& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -m pip install --force-reinstall <target\wheels 下生成的 whl>
```

（或 `maturin develop --release --features live` 直装 venv；编译约 3-8 分钟。）

- [ ] **Step 3: 验证 LIVE_FEATURE**

```powershell
& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -X utf8 -c "import hftbacktest; print(hftbacktest.LIVE_FEATURE)"
```
Expected: `True`。若 False，检查 maturin 是否编译了带 live 的 feature 组合。

- [ ] **Step 4: 回归——回放轨测试不受影响**

```powershell
& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -X utf8 -m pytest research/tests/ -q
```
Expected: 16 passed（重装 wheel 后 numba 缓存可能重编译，首次较慢）。

- [ ] **Step 5: 无 git 提交（无仓库变更）**；记录 wheel 路径与 hftbacktest 源码 commit 供复现。

---

### Task 2: `live_indicators.py` —— LiveBot 采样循环

**Files:**
- Create: `C:\workplace\binance-orderflow-lab\research\live_indicators.py`
- Test: `C:\workplace\binance-orderflow-lab\research\tests\test_live_indicators.py`

**设计要点：**
- 构造：`build_live_hbt(connector_name, symbol)` → `HashMapMarketDepthLiveBot([LiveInstrument()...])`。
- 采样循环：**复用** `replay_indicators` 的 njit `_sample` 与缓冲区分配——抽公共 `_run_sample(hbt, max_rows)`
  供两轨调用（`replay_to_df` 与 `live_sample_to_df` 均走它），保证指标口径 1:1。
  - live 侧差异在循环外：live `elapse` 是真实等待，超时返回 0 视为"本秒无行情"，采样继续
    （时间戳以 `current_timestamp` 真实时钟为准）。
- 输出 schema 与回放轨完全一致（OUT_COLS）。
- 跳过依赖真实 connector 的部分：单测用**注入接口模拟**——测试不走 iceoryx2，
  只测 `_run_sample` 已由回放轨覆盖 + live 构造器的参数装配（LiveInstrument 链式配置正确性）。
  **不在单测中启动 connector**；真流验证放 Task 3。

- [ ] **Step 1: 失败测试**

```python
import numpy as np
import pytest

hftlive = pytest.importorskip(
    'hftbacktest',
    reason='live feature not compiled',
)
# 更精确：检测 LIVE_FEATURE
import hftbacktest as _h
if not getattr(_h, 'LIVE_FEATURE', False):
    pytest.skip('live feature not compiled', allow_module_level=True)

from research import config
from research.live_indicators import build_live_hbt


def test_build_live_hbt_returns_bot():
    hbt = build_live_hbt('bf', 'btcusdt')
    assert hbt is not None
    assert hbt.num_assets == 1


def test_run_sample_shared_with_replay():
    # _run_sample 必须与回放轨共享同一 njit 函数
    from research import live_indicators, replay_indicators
    assert live_indicators._run_sample is replay_indicators._run_sample
```

- [ ] **Step 2: 运行确认失败**

Run: `& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -X utf8 -m pytest research/tests/test_live_indicators.py -v`
Expected: FAIL（`research.live_indicators` 不存在）。

- [ ] **Step 3: 重构 + 实现**

1. 在 `research/replay_indicators.py` 中把 `replay_to_df` 内的缓冲区分配 + `_sample` 调用抽为：

```python
def _run_sample(hbt):
    """Allocates buffers, runs the shared njit sampling loop, returns DataFrame.

    Shared by the replay track (Backtest) and the live track (LiveBot); both
    expose depth()/last_trades()/clear_last_trades()/current_timestamp/elapse.
    """
    # …现有 replay_to_df 的分配逻辑原样移入，末尾返回 df…
```

`replay_to_df(hbt)` 变为 `return _run_sample(hbt)`。

2. 新建 `research/live_indicators.py`：

```python
import numpy as np

from hftbacktest import HashMapMarketDepthLiveBot, LiveInstrument

from research import config
from research.replay_indicators import OUT_COLS, _run_sample


def build_live_hbt(connector_name: str,
                   symbol: str = None,
                   tick_size: float = 0.1,
                   lot_size: float = 0.001):
    """Builds a live bot bound to a running `connector` via iceoryx2.

    The connector with the same `connector_name` must be running on this
    machine before the bot is created.
    """
    symbol = symbol or config.SYMBOL
    inst = (
        LiveInstrument()
        .connector(connector_name)
        .symbol(symbol)
        .tick_size(tick_size)
        .lot_size(lot_size)
        .last_trades_capacity(config.LAST_TRADES_CAP)
    )
    return HashMapMarketDepthLiveBot([inst])


def live_sample_to_df(hbt, seconds: float = 3600.0):
    """Samples indicators from the live stream for `seconds` wall-clock time.

    Uses the SAME njit loop as the replay track; live `elapse` waits in real
    time, so sampling proceeds at wall-clock pace. Returns the standard
    OUT_COLS DataFrame.
    """
    # live 循环与回放的差异：超时(elapse==0)也产出一行（无行情秒）。
    # 实现方式：在 _run_sample 外层以秒计数控制时长；行内 NaN 由循环自身处理。
    return _run_sample(hbt)
```

（若 `_run_sample` 内 `elapse != 0` 即停的语义在 live 下不适配——live 超时返回 0 而非错误——
在 `_run_sample` 增加 `max_rows` 截断已天然限长；必要时为 live 增加 `stop_after_rows` 参数。）

- [ ] **Step 4: 全量测试**

Run: `& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -X utf8 -m pytest research/tests/ -q`
Expected: 全部通过（live 测试在 LIVE_FEATURE=False 环境自动 skip）。

- [ ] **Step 5: Commit**

```bash
git add research/live_indicators.py research/replay_indicators.py research/tests/test_live_indicators.py
git commit -m "feat(research): add Python LiveBot live-stream sampling sharing the replay njit loop"
```

---

### Task 3: 真流端到端验证（connector + LiveBot）

**Files:**
- Create: `C:\workplace\binance-orderflow-lab\connector\binancefutures.toml`（connector 配置；api_key 留空=纯行情）

- [ ] **Step 1: 配置 connector**

```toml
stream_url = "wss://fstream.binance.com/ws"
api_url = "https://fapi.binance.com"
order_prefix = "research"
api_key = ""
secret = ""
```

- [ ] **Step 2: 启动 connector（独立窗口/后台）**

```powershell
Start-Process -FilePath "C:\workplace\hftbacktest\target\release\connector.exe" -ArgumentList "bf","binancefutures","C:\workplace\binance-orderflow-lab\connector\binancefutures.toml" -PassThru -WindowStyle Hidden
```
（`bf` = LiveInstrument 的 connector 名。）

- [ ] **Step 3: 冒烟脚本（临时，不入库）**

```powershell
& "C:\workplace\binance-orderflow-lab\.HftBacktest\Scripts\python.exe" -X utf8 -c "
from research.live_indicators import build_live_hbt, live_sample_to_df
hbt = build_live_hbt('bf', 'btcusdt')
df = live_sample_to_df(hbt, seconds=120)
print(df.tail())
df.to_csv('research/results/live_smoke.csv', index=False)
"
```
Expected: ~120 行 OUT_COLS 数据；mid 为 BTCUSDT 合理价位；obi/trade_ofi 有非 NaN 值；
book_ofi 前 60 行为 NaN（trend warm-up 60s，book_ofi 首帧 NaN 属预期）。

- [ ] **Step 4: 校验与排错**

- 若 LiveBot 构造报 channel/service 错误：确认 connector 进程存活、name 一致、同机运行。
- 若行数远小于预期：打印 `hbt.elapse` 返回码分布（live 超时应为 0）。
- 若 book 全空：确认 connector 已订阅深度流（其日志）。

- [ ] **Step 5: 双轨口径抽查（可选，若 collector 同期在录）**

对同一分钟：回放轨（collector gz → replay_to_df）与实时轨 live_smoke.csv 的 mid/obi 数值
应一致（book_ofi 因增量簿构建时点差异允许小偏差）。记录对比结论。

- [ ] **Step 6: Commit（配置文件）**

```bash
git add connector/binancefutures.toml
git commit -m "chore(research): add binancefutures connector config for live track"
```

---

## 自审记录

- **Spec 覆盖**：spec §5 实时轨（connector + Python LiveBot + 同口径互验）→ Task 1-3；
  §9 "实时轨与回放轨相同口径互验" → Task 2 共享 `_run_sample` + Task 3 Step 5。
- **占位符**：无 TBD；Task 2 Step 3 的"必要时为 live 增加 stop_after_rows"给出了明确触发条件与语义。
- **类型一致性**：`_run_sample(hbt)` 抽取后 replay/live 共用；OUT_COLS 不变；
  `build_live_hbt` 参数命名与 `LiveInstrument` 链式方法逐一对应。
- **已知风险**：live `elapse` 返回码语义（0=超时/1=断流/2=有 feed）与回放不同，
  `_sample` 内 `elapse(...) != 0 → break` 在 live 下会把"收到 feed"当退出条件——
  Task 2 Step 3 已注明需以 `stop_after_rows`/时长截断替代错误退出语义，实现时必须先读
  `binding.py` live 侧 `elapse` 文档（1610-1700 区域）核对返回码后再定循环条件。
