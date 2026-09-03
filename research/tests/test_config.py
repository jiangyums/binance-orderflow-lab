from research import config


def test_config_values():
    assert config.SYMBOL.upper() == 'BTCUSDT'
    assert config.SAMPLE_INTERVAL_MS == 1000
    assert config.TREND_WINDOW_MS == 60_000
    assert config.FUTURE_HORIZONS_S == [5, 15, 60]
    assert config.TAKER_FEE == 0.0005
    assert config.BOOK_OFI_LEVELS == 20
    assert config.DROP_SMALL_ABS_FRAC == 0.10
    assert config.SECONDS_PER_DAY == 86_400
    assert config.SIGNIFICANCE_ALPHA == 0.05
