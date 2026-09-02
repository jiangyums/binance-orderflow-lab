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
