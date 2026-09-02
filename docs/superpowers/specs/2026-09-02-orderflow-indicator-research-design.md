# 订单流指标（OBI / tradeOFI / bookOFI / 60s 趋势）预测力研究 — 设计文档

日期：2026-09-02
状态：已确认设计，待实现
仓库：`C:\workplace\binance-orderflow-lab`（独立仓库，`github.com/jiangyums/binance-orderflow-lab`）

## 1. 背景与目标

在现有 `binance-orderflow-lab` 独立仓库基础上，集成 hftbacktest，研究四个市场微观结构指标对
Binance BTCUSDT USD-M 永续未来短期收益的预测能力：

- **OBI**（Order Book Imbalance，盘口不平衡）
- **tradeOFI**（Trade Order Flow Imbalance，逐笔订单流不平衡）
- **bookOFI**（Book Order Flow Imbalance，盘口流不平衡）
- **60 秒趋势**（当前短周期趋势）

研究输出：
1. 指标方向对未来收益的**命中率**与**分位数分组收益**（预测力检验）。
2. 基于指标的**简单开平仓策略**每笔胜率、累计利润等（含 Binance 实际费率）。

**原则**：能用 hftbacktest 的功能尽量用 hftbacktest，除非其不能满足。Python 指标先做实验
（阶段 A），跑通后迁移为 Rust（阶段 B）。

**范围边界**：仅研究分析，不实盘下单。阶段 B 仅到"实时采集 + 指标计算 + 信号统计"，不接交易所下单。

## 2. 与现有仓库的关系

- 仓库中 **2026-08-31 的 Go 重构设计文档（Approved）标记为 superseded**，转向 Rust 方案。
- 现有 `internal/`（Go）、`src/orderflow/`（Python）、`tests/` 生产代码**保留**，作为实时采集参考；
  自建 `OrderBook` / U-u 同步逻辑（`binance_depth.py` 等）不再需要维护。
- 新增 `research/`（阶段 A 实验）与 `rust/`（阶段 B 实现），不动现有代码。

## 3. 阶段划分

### 阶段 A：研究（Python + hftbacktest 绑定）

```
data.binance.vision ──binancehistmktdata.convert──> npz
    └─> hftbacktest Backtest 引擎回放（pyo3 绑定）
        └─> 1 秒采样：OBI / tradeOFI / bookOFI / 60s 趋势
            └─> 命中率(5/15/60s) + 分位数分组 + 简单开平仓策略
                └─> report.md + CSV + 图表
```

### 阶段 B：生产（Rust + hftbacktest Rust API）

```
hftbacktest Rust collector（binancefuturesum）实时采集 → npz
    └─> Rust 版指标实现（L2AssetBuilder / Backtest / HashMapMarketDepth）
        └─> 同一套 Bot trait 接口，回测与实盘同构
```

## 4. 目录结构

```
binance-orderflow-lab/
├── research/                    # 新增【阶段 A】Python 实验
│   ├── config.py                # symbol/日期范围/采样频率/预测窗口/费率/路径
│   ├── prepare_data.py          # data.binance.vision 下载 → 转 hftbacktest npz
│   ├── replay_indicators.py     # hftbacktest Backtest 回放，1s 采样四指标
│   ├── analyze.py               # 命中率 / 分位数 / 简单开平仓统计
│   ├── report.py                # report.md + CSV + 图表
│   ├── run.py                   # 主入口：prepare → replay → analyze → report
│   └── tests/                   # 合成数据单测 + 随机游走 sanity check
├── rust/                        # 新增【阶段 B】Rust 实现（Cargo crate）
│   ├── Cargo.toml               # 依赖 hftbacktest crate
│   └── src/
│       ├── indicators.rs        # 四指标 Rust 实现
│       └── main.rs              # 采集/回放入口
├── internal/  src/  tests/      # 现有 Go + Python 代码（保留）
└── docs/superpowers/            # 设计文档（Go 重构设计标记 superseded）
```

## 5. 数据管线

- **研究阶段**：从 data.binance.vision 下载近 1–2 周（默认 7 天）BTCUSDT USD-M 数据包
  （`aggTrades` + `bookDepth`），用 `hftbacktest.data.utils.binancehistmktdata.convert`
  转成 hftbacktest 兼容 npz，补初始快照（`DEPTH_SNAPSHOT`），`validate_event_order` 校验事件顺序。
- **生产阶段**：hftbacktest Rust `collector` crate 的 `binancefuturesum` 实时采集，直接写 npz。
- 缺失日期记 gap，报告中注明。

## 6. 指标定义（hftbacktest 回放内实现，1 秒采样）

| 指标 | hftbacktest 内取数方式 | 公式 |
|---|---|---|
| OBI | `depth.best_bid_qty` / `best_ask_qty` | `(bid_qty − ask_qty) / (bid_qty + ask_qty)` |
| tradeOFI | `last_trades`（含 taker 方向），秒内聚合 | `(主动买量 − 主动卖量) / (主动买量 + 主动卖量)` |
| bookOFI | `bid_qty_at_tick` / `ask_qty_at_tick` 相邻秒差分（前 20 档，等权） | `ΔB − ΔA` |
| 60s 趋势 | `mid_price` 过去 60 秒变化率 | `(mid_t − mid_{t−60s}) / mid_{t−60s}` |

缺失值用 NaN 表示并在统计时剔除。

## 7. 统计口径

### 7.1 方向命中率

- 采样点 t：指标值 + 未来收益 `r_h = (mid_{t+h} − mid_t) / mid_t`，`h ∈ {5, 15, 60}s`。
- 命中率 = `sign(指标) == sign(r_h)` 占比；剔除 `|指标|` < 其分布第 10 百分位的样本。
- 每 指标 × 窗口 报告：命中率、样本数、binomial 显著性。

### 7.2 分位数分组收益

- 每指标分 5 组（Q1 最负 → Q5 最正），报告各组未来收益均值 / 标准差 / 样本数，观察单调性。

### 7.3 简单开平仓策略

- 触发：指标 Z-score（滚动 300s）绝对值 > 1.5 建仓，方向 = sign(指标)；持仓 h 秒全平（taker 全进全出）。
- 成本：taker 0.05% 双边（开+平各一次），报告含 / 不含手续费两种结果。
- 分别运行：单指标 + 多指标简单多数投票。
- 统计：每笔胜率、平均盈亏、累计利润、最大回撤、Sharpe（按持仓周期年化）、交易次数。

## 8. 与 hftbacktest 的接口边界

| 阶段 | 调用方式 | 使用接口 |
|---|---|---|
| 阶段 A | Python 绑定 | `BacktestAsset`、`HashMapMarketDepthBacktest`、`BUY/SELL/GTX/LIMIT`、`Bot`（`elapse`/`depth`/`last_trades`/`position`）、`hftbacktest.data.utils.binancehistmktdata` |
| 阶段 B | Rust API | `L2AssetBuilder`、`Backtest`、`HashMapMarketDepth`、`Bot` trait、`collector` crate |

不 import hftbacktest 私有模块、不改动其源码；接口缺失或 bug 在 hftbacktest 仓库提 issue/PR。

## 9. 工程性与验证

- `prepare_data.py` 下载后校验 zip 完整性；缺失日期记 gap。
- `research/tests/`：合成小数据集断言四指标与手算值一致；随机游走 sanity check（命中率≈50%）。
- 阶段 B 与阶段 A 用**相同口径报表**做交叉验证（数值一致性检查）。
- 参数集中在 `research/config.py`；`python -m research.run --start --end` 指定日期。
- 迁移契约：`replay_indicators.py` 输出固定秒级 schema
  （timestamp, mid, obi, trade_ofi, book_ofi, trend, bid_qty, ask_qty），阶段 B Rust 按同一 schema 输出 CSV。

## 10. 输出

- `results/report.md`：统计结果汇总。
- `results/`：每指标每窗口 CSV。
- `results/*.png`：命中率热力图、分位数收益图、策略净值曲线。

## 11. 明确不做（YAGNI）

- 不实盘自动交易；阶段 B 不含交易所下单。
- 不做复杂组合优化；多指标投票限于简单多数。

## 12. 未知项与风险

- data.binance.vision 各数据包 CSV 确切字段名 / 单位 / 时间戳格式未核实，实现第一步须下载样例验证。
- `bookDepth` 极端行情可能缺失个别帧，导致 bookOFI 差分失真（用前一个有效帧代替，报告注明 gap）。
- 历史数据回放无撮合滑点，简单策略成交假设（taker 按当前盘口成交）偏理想化。
- 阶段 B 的 hftbacktest Rust `collector` 对 Binance USD-M 的深度管理当前仅支持自然刷新（见 hftbacktest #300 issue），实时采集的订单簿精度以 BBO 为主。
