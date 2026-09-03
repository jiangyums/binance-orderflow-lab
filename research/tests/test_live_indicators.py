import numpy as np
import pytest

import hftbacktest as _h

if not getattr(_h, 'LIVE_FEATURE', False):
    pytest.skip('live feature not compiled', allow_module_level=True)

from research import live_indicators, replay_indicators


def test_run_sample_shared_with_replay():
    # live 与 replay 必须共享同一 njit 采样函数（指标口径 1:1）
    assert live_indicators._run_sample is replay_indicators._run_sample


def test_build_live_hbt_returns_bot():
    hbt = live_indicators.build_live_hbt('bf', 'btcusdt')
    assert hbt is not None
    assert hbt.num_assets == 1


def test_out_cols_consistent():
    assert live_indicators.OUT_COLS == replay_indicators.OUT_COLS
