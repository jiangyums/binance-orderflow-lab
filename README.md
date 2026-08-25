# binance-orderflow-lab

Binance USDⓈ-M Futures 订单流（order flow）实验场：L2 盘口采集 → 特征计算 → 信号生成 → 收益评估。

## 依赖

- Python 3.11+
- `aiohttp`（REST 快照）
- `websockets`（行情 WebSocket）

## 环境搭建

```powershell
python -m venv .HftBacktest
& .\.HftBacktest\Scripts\Activate.ps1
pip install aiohttp websockets
```

> 仓库已通过 `.gitignore` 排除 `.HftBacktest/`、`data/`（运行时产物）、`.opencode/`。
> 克隆后需自行创建虚拟环境并安装依赖。

## 运行

### 1. 采集盘口 + 成交流，落盘 CSV

```powershell
python -m src.orderflow.collector.main
```

- depth worker：`/fapi/v1/depth` 快照 + `@depth@100ms` 增量流，自动同步；断线/序列不连续时自动重连并重新快照同步。
- trade worker：`@trade` 成交流。
- 实时特征写入 `data/features.csv`，信号与收益写入 `data/evaluation.csv`。

> 直连 Binance 可能受网络限制；如处于需要代理的环境，请先配置好代理再运行。

### 2. 查看信号统计

```powershell
python -m tests.test_signal_statistics
```

读取 `data/evaluation.csv`，打印分信号、分强度档位的胜率与 avg_ret（正=盈利）。

### 3. 阈值扫描（确信度甜点区分析）

```powershell
# 先录制一批 features.csv（同一会话，保证同口径）
python -m src.orderflow.collector.main
# Ctrl+C 停止后，用这一批固定数据扫不同 emit 阈值
python -m tests.threshold_sweep
#   可选：--fee 0.0002（maker） / --thresholds 0.4 0.5 0.6 0.7 0.8 0.9
```

脚本用**同一批** `data/features.csv` 离线回放，依次以不同 emit 阈值跑通
`SignalEngine` → `SignalStateTracker` → 收益计算（复用生产代码路径，只改变阈值），
输出每个阈值下的样本数、胜率、毛收益与净收益：

| 列 | 含义 |
|----|------|
| `samples` | 该阈值实际发出的 LONG/SHORT 信号数（已去重） |
| `winX%` / `retX` | X = 1/5/10s 的胜率 / 毛收益（mid-to-mid） |
| `netX` | 扣成本后的净收益 |
| `cost` | 平均往返成本（见下） |

**成本模型（关键点）**：`net` 不是拍脑袋的常数，而是从录制数据里**真实的
`spread` 列**算出来的：

```
cost_X = 半点差(入场) + 半点差(出场@Xs) + 2 × fee
半点差   = spread / (2 × mid)
```

- `spread` / `mid` 取自 `features.csv` 每个信号发生时刻的真实盘口；
- `fee` 为单边手续费（`--fee`，默认 0.0004 = 0.04% taker；maker 约 0.0002）；
- 毛收益本身是 mid-to-mid，已偏乐观；这里用真实点差把"无法按中间价成交"
  的成本补回来，因此 `net` 比固定 0.1% 的猜测可靠得多。

> 实测结论（BTCUSDT，fee=0.04%/side）：胜率随阈值升高而升高，确信度轴有效；
> 但每笔毛收益仅 ~0.01%–0.02%，而真实往返成本约 **0.08%**（BTC 点差极小，
> 主要由手续费主导），所以 taker 成本下**所有阈值均净负**。即便压到最低 maker
> （~0.02% 往返），也只有最高确信度 + 10s 档位勉强转正——盈亏由执行成本主导。

## 目录结构

```
src/orderflow/
  book/          # OrderBook（绝对数量 + 0 删除语义）
  collector/     # Binance WebSocket / REST 采集与重连
  features/      # OBI / MicroPrice / OFI / CVD
  signal/        # SignalEngine（LONG / SHORT / FLAT）
  evaluator/     # 收益评估（mid-to-mid 多周期收益）
  statistics/    # 胜率 / 收益统计报告
  events/        # 事件队列与处理管线
tests/           # 单元测试 / 统计脚本
```
