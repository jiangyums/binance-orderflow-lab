SYMBOL = 'btcusdt'

# 数据时间戳单位 = 纳秒（binancefutures.convert: transaction_time(ms) * 1_000_000）
SAMPLE_INTERVAL_MS = 1000      # 1s 采样（毫秒语义，供分析层文档使用）
SAMPLE_INTERVAL_NS = SAMPLE_INTERVAL_MS * 1_000_000   # elapse 用：与数据单位一致
TREND_WINDOW_MS = 60_000       # 60s 趋势窗口
TREND_WINDOW_NS = TREND_WINDOW_MS * 1_000_000

# 默认研究日期范围（近 1 周；数据来自 data/rec/ 下的 collector 录制）
START_DATE = '2026-09-03'
END_DATE = '2026-09-03'

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

# 统计分析参数
DROP_SMALL_ABS_FRAC = 0.10     # hit-rate 中剔除 |indicator| 过小样本的分位阈值
SECONDS_PER_DAY = 86_400       # 秒/天，用于 Sharpe 近似
SIGNIFICANCE_ALPHA = 0.05      # hit-rate 显著性检验阈值

# 数据
DATA_DIR = 'data'
RESULTS_DIR = 'research/results'
CACHE_DIR = 'data/hist'
