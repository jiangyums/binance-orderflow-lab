import gzip
import json
import os
import tempfile

import numpy as np

from hftbacktest.types import (
    BUY_EVENT, SELL_EVENT, TRADE_EVENT, DEPTH_EVENT, event_dtype,
)

from research import config, prepare_data


def _collector_lines():
    """Synthesizes collector-format lines: ``{ns_recv_time} {combined_stream_json}``.

    The Rust collector records combined-stream messages:
    ``{"stream":"btcusdt@...","data":{...}}``.
    """
    base_ns = 1_660_000_000_000_000_000

    def combined(stream, data):
        return json.dumps({'stream': stream, 'data': data})

    lines = []
    # depthUpdate: bid 24670.9 x2.5, ask 24671.0 x1.5 (T in ms)
    depth = {
        'e': 'depthUpdate', 'E': 1660000000001, 'T': 1660000000000,
        's': 'BTCUSDT', 'U': 1, 'u': 2, 'pu': 0,
        'b': [['24670.90', '2.500']],
        'a': [['24671.00', '1.500']],
    }
    lines.append(f'{base_ns} {combined("btcusdt@depth@0ms", depth)}')
    # MARKET trade: buyer is taker -> BUY_EVENT (m=false)
    trade = {
        'e': 'trade', 'E': 1660000005001, 'T': 1660000005000,
        's': 'BTCUSDT', 't': 1, 'p': '24670.90', 'q': '0.500',
        'X': 'MARKET', 'm': False,
    }
    lines.append(f'{base_ns + 5_000_000_000} {combined("btcusdt@trade", trade)}')
    # MARKET trade: seller is taker -> SELL_EVENT (m=true)
    trade2 = {
        'e': 'trade', 'E': 1660000006001, 'T': 1660000006000,
        's': 'BTCUSDT', 't': 2, 'p': '24671.00', 'q': '0.300',
        'X': 'MARKET', 'm': True,
    }
    lines.append(f'{base_ns + 6_000_000_000} {combined("btcusdt@trade", trade2)}')
    # non-MARKET trade must be skipped by the converter
    trade3 = {
        'e': 'trade', 'E': 1660000007001, 'T': 1660000007000,
        's': 'BTCUSDT', 't': 3, 'p': '24671.00', 'q': '0.100',
        'X': 'LIMIT', 'm': False,
    }
    lines.append(f'{base_ns + 7_000_000_000} {combined("btcusdt@trade", trade3)}')
    return '\n'.join(lines) + '\n'


def test_config_units():
    # collector feed timestamps are nanoseconds (ms * 1_000_000)
    assert config.SAMPLE_INTERVAL_NS == 1_000_000_000
    assert config.TREND_WINDOW_NS == 60_000_000_000


def test_convert_rec_produces_expected_events():
    with tempfile.TemporaryDirectory() as td:
        gz = os.path.join(td, 'btcusdt_20260903.gz')
        with gzip.open(gz, 'wt') as f:
            f.write(_collector_lines())
        out_npz = os.path.join(td, 'feed.npz')

        data = prepare_data.convert_rec(gz, out_npz, buffer_size=1000)

        # depth rows (1 bid + 1 ask) + 2 MARKET trades; LIMIT trade skipped
        assert len(data) == 4
        loaded = np.load(out_npz)['data']
        assert len(loaded) == 4
        assert (loaded['ev'] & DEPTH_EVENT).any()
        assert (loaded['ev'] & TRADE_EVENT).any()
        assert (loaded['ev'] & BUY_EVENT).any()
        assert (loaded['ev'] & SELL_EVENT).any()
        # timestamps are nanoseconds (ms * 1_000_000)
        assert loaded['exch_ts'][0] == 1_660_000_000_000_000_000


def test_rec_gz_paths_finds_files():
    with tempfile.TemporaryDirectory() as td:
        rec = os.path.join(td, 'rec')
        os.makedirs(rec)
        open(os.path.join(rec, 'btcusdt_20260902.gz'), 'w').close()
        open(os.path.join(rec, 'btcusdt_20260903.gz'), 'w').close()
        open(os.path.join(rec, 'other.csv'), 'w').close()
        paths = prepare_data.rec_gz_paths(td)
        assert len(paths) == 2
        assert all(p.endswith('.gz') for p in paths)
        assert paths[0].endswith('btcusdt_20260902.gz')


def test_prepare_day_missing_recording_raises():
    with tempfile.TemporaryDirectory() as td:
        try:
            prepare_data.prepare_day('2020-01-01', td)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError('expected FileNotFoundError')


def test_prepare_range_skips_missing_days():
    with tempfile.TemporaryDirectory() as td:
        rec = os.path.join(td, 'rec')
        os.makedirs(rec)
        gz = os.path.join(rec, 'btcusdt_20260903.gz')
        with gzip.open(gz, 'wt') as f:
            f.write(_collector_lines())

        out = prepare_data.prepare_range('2026-09-01', '2026-09-03', td)
        # 09-01/09-02 missing -> skipped; 09-03 converted
        assert len(out) == 1
        assert os.path.exists(out[0]['feed'])
        assert out[0]['snapshot'] is None
