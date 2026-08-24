from src.orderflow.statistics.signal_statistics import (
    SignalStatistics
)



stats = SignalStatistics()


stats.load(
    "data/evaluation.csv"
)


stats.report()