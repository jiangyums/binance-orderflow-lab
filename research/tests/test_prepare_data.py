import gzip
import os
import tempfile
import zipfile

import numpy as np

from hftbacktest.data.utils import binancehistmktdata

from research import prepare_data


def test_read_zip_text_plain_and_gz():
    with tempfile.TemporaryDirectory() as td:
        plain_zip = os.path.join(td, 'plain.zip')
        with zipfile.ZipFile(plain_zip, 'w') as zf:
            zf.writestr('BTCUSDT-depth.csv', 'symbol,timestamp\nBTCUSDT,1\n')
        assert prepare_data._read_zip_text(plain_zip) == 'symbol,timestamp\nBTCUSDT,1\n'

        gz_zip = os.path.join(td, 'gz.zip')
        with zipfile.ZipFile(gz_zip, 'w') as zf:
            zf.writestr('BTCUSDT-depth.csv.gz', gzip.compress(b'symbol,timestamp\nBTCUSDT,1\n'))
        assert prepare_data._read_zip_text(gz_zip) == 'symbol,timestamp\nBTCUSDT,1\n'


def test_read_zip_text_empty_raises():
    with tempfile.TemporaryDirectory() as td:
        empty_zip = os.path.join(td, 'empty.zip')
        with zipfile.ZipFile(empty_zip, 'w'):
            pass
        try:
            prepare_data._read_zip_text(empty_zip)
        except ValueError as exc:
            assert 'no members' in str(exc)
        else:
            raise AssertionError('expected ValueError for empty zip')


def test_convert_hist_depth_trades_roundtrip():
    # 构造 data.binance.vision 格式的 depth CSV 与 aggTrades CSV
    depth_csv = (
        'symbol,timestamp,trans_id,first_update_id,last_update_id,side,update_type,price,qty\n'
        'BTCUSDT,1660000000000,1,100,200,b,0,24670.90,2.5\n'
        'BTCUSDT,1660000000000,2,201,300,a,0,24671.00,1.5\n'
    )
    trades_csv = (
        'id,price,qty,quote_qty,time,is_buyer_maker\n'
        '1,24670.90,0.5,12335.45,1660000000000,false\n'
        '2,24671.00,0.3,7401.30,1660000001000,true\n'
    )
    with tempfile.TemporaryDirectory() as td:
        d = os.path.join(td, 'depth.csv')
        t = os.path.join(td, 'trades.csv')
        out = os.path.join(td, 'out.npz')
        with open(d, 'w') as f:
            f.write(depth_csv)
        with open(t, 'w') as f:
            f.write(trades_csv)
        arr = binancehistmktdata.convert(d, t, out)
        assert len(arr) == 4
        loaded = np.load(out)['data']
        assert len(loaded) == 4
        assert (loaded['ev'] & 2).any()   # TRADE_EVENT present
        assert (loaded['ev'] & 1).any()   # DEPTH_EVENT present
        # depth side: b -> BUY_EVENT, a -> SELL_EVENT
        assert (loaded['ev'] & (1 << 29)).any()
        assert (loaded['ev'] & (1 << 28)).any()


def test_download_url_template():
    url = prepare_data.hist_data_url('aggTrades', '2026-08-26')
    assert url == (
        'https://data.binance.vision/data/futures/um/daily/BTCUSDT/aggTrades/'
        'BTCUSDT-aggTrades-2026-08-26.zip'
    )


def test_download_url_template_bookdepth():
    url = prepare_data.hist_data_url('bookDepth', '2026-08-26')
    assert url == (
        'https://data.binance.vision/data/futures/um/daily/BTCUSDT/bookDepth/'
        'BTCUSDT-bookDepth-1000-2026-08-26.zip'
    )
