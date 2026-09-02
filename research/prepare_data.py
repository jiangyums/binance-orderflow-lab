import gzip
import os
import zipfile

import requests

from research import config

BASE_URL = 'https://data.binance.vision/data/futures/um/daily'
DEPTH_LEVEL = 1000


def hist_data_url(book_type: str, date: str) -> str:
    sym = config.SYMBOL.upper()
    fname = f'{sym}-{book_type}-{date}.zip'
    if book_type == 'bookDepth':
        fname = f'{sym}-{book_type}-{DEPTH_LEVEL}-{date}.zip'
    return f'{BASE_URL}/{sym}/{book_type}/{fname}'


def download_zip(url: str, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    fname = os.path.basename(url)
    dest = os.path.join(dest_dir, fname)
    if os.path.exists(dest):
        return dest
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    with open(dest, 'wb') as f:
        f.write(resp.content)
    return dest


def _read_zip_text(path: str) -> str:
    with zipfile.ZipFile(path) as zf:
        name = zf.namelist()[0]
        raw = zf.read(name)
    if name.endswith('.gz'):
        raw = gzip.decompress(raw)
    return raw.decode('utf-8')


def prepare_day(date: str, data_dir: str = config.DATA_DIR) -> dict:
    cache = os.path.join(data_dir, 'hist', date)
    os.makedirs(cache, exist_ok=True)

    agg = download_zip(hist_data_url('aggTrades', date), cache)
    depth = download_zip(hist_data_url('depth', date), cache)
    bookdepth_ok = True
    try:
        bookdepth = download_zip(hist_data_url('bookDepth', date), cache)
    except Exception:
        bookdepth = None
        bookdepth_ok = False

    trades_txt = os.path.join(cache, 'trades.csv')
    depth_txt = os.path.join(cache, 'depth.csv')
    snap_txt = os.path.join(cache, 'snapshot.csv')

    with open(trades_txt, 'w', newline='') as f:
        f.write(_read_zip_text(agg))
    with open(depth_txt, 'w', newline='') as f:
        f.write(_read_zip_text(depth))

    from hftbacktest.data.utils import binancehistmktdata

    feed_npz = os.path.join(cache, 'feed.npz')
    binancehistmktdata.convert(depth_txt, trades_txt, feed_npz, buffer_size=200_000_000)

    result = {'feed': feed_npz, 'snapshot': None}
    if bookdepth_ok:
        with open(snap_txt, 'w', newline='') as f:
            f.write(_read_zip_text(bookdepth))
        snap_npz = os.path.join(cache, 'snapshot.npz')
        binancehistmktdata.convert_snapshot(snap_txt, snap_npz)
        result['snapshot'] = snap_npz
    return result


def prepare_range(start: str, end: str, data_dir: str = config.DATA_DIR) -> list:
    from datetime import date, timedelta

    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    out = []
    d = s
    while d <= e:
        iso = d.isoformat()
        try:
            out.append(prepare_day(iso, data_dir))
        except Exception as exc:
            print(f'[prepare] {iso} skipped: {type(exc).__name__}: {exc}')
        d += timedelta(days=1)
    return out
