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
