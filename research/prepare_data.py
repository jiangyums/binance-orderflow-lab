import gzip
import io
import json
import os
import shutil
import zlib

import numpy as np

from hftbacktest.data.utils import binancefutures

from research import config

REC_DIR_NAME = 'rec'


def _recover_gzip(src: str, dest: str) -> None:
    """Recovers a readable gzip copy from a possibly-still-being-written recording.

    The collector keeps a single gzip stream open for the whole day, so the
    in-progress file has no valid CRC trailer and its tail may end mid-block.
    We decompress as far as possible (dropping any trailing partial line) and
    re-compress the recovered plaintext into a valid gzip file.
    """
    with open(src, 'rb') as f:
        raw = f.read()

    d = zlib.decompressobj(wbits=-15)
    plain = bytearray()
    payload = raw[10:]  # skip gzip header; trailer (if any) is 8 bytes
    chunk = 1 << 16
    pos = 0
    try:
        while pos < len(payload):
            plain += d.decompress(payload[pos:pos + chunk])
            pos += chunk
    except zlib.error:
        pass  # stream still in progress; keep what decompressed cleanly

    # Line-level validation: zlib may emit garbage bytes just before the
    # corruption point, and a live copy may tear mid-write. Accept only the
    # leading run of well-formed ``{ns} {json}`` lines; truncate the rest.
    good_end = 0
    for i, ln in enumerate(plain.split(b'\n')):
        try:
            s = ln.decode('utf-8')
            sp = s.index(' ')
            int(s[:sp])
            json.loads(s[sp + 1:])
            good_end = i + 1
        except Exception:
            break
    lines = plain.split(b'\n')[:good_end]
    text = b'\n'.join(lines)
    with gzip.open(dest, 'wb') as f:
        f.write(text + b'\n' if text else b'')


def rec_gz_paths(data_dir: str = config.DATA_DIR) -> list:
    """Lists collector output files ``{symbol}_{YYYYMMDD}.gz`` under data/rec."""
    rec = os.path.join(data_dir, REC_DIR_NAME)
    if not os.path.isdir(rec):
        return []
    sym = config.SYMBOL.lower()
    return sorted(
        os.path.join(rec, f)
        for f in os.listdir(rec)
        if f.startswith(sym) and f.endswith('.gz')
    )


def _copy_locked(src: str, dest_dir: str) -> str:
    """Makes a readable copy of a possibly in-progress recording.

    First tries a plain copy and fully verifies it as a gzip stream (works for
    finished files with a valid trailer). If verification fails (single gzip
    stream still being written, or the copy tore mid-write), falls back to
    ``_recover_gzip``, which decompresses as far as possible and keeps only
    the leading run of well-formed lines. A snapshot copy may miss the last
    few in-flight messages, which is acceptable for research purposes.
    """
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(src))
    shutil.copyfile(src, dest)
    try:
        with gzip.open(dest, 'rb') as f:
            while f.read(1 << 22):
                pass
        return dest
    except (gzip.BadGzipFile, EOFError, zlib.error, OSError):
        recovered = dest + '.recovered.gz'
        _recover_gzip(src, recovered)
        os.remove(dest)
        return recovered


def convert_rec(gz_path: str, output_npz: str, buffer_size: int = 100_000_000) -> np.ndarray:
    """Converts a collector recording (``{ns} {raw_json}`` lines, gzipped) into a
    hftbacktest-compatible npz feed via ``binancefutures.convert``.

    The collector writes combined-stream messages (``{"stream":..,"data":{..}}``),
    so ``combined_stream=True`` is passed. Timestamps in the output are
    nanoseconds (``transaction_time(ms) * 1_000_000``).
    """
    return binancefutures.convert(
        gz_path,
        output_npz,
        buffer_size=buffer_size,
        combined_stream=True,
    )


def prepare_day(date: str, data_dir: str = config.DATA_DIR) -> dict:
    """Converts the collector recording for ``date`` (YYYY-MM-DD) into feed npz.

    Looks for ``data/rec/{symbol}_{YYYYMMDD}.gz``. If the recording is the
    active (locked) file for today, a copy is converted. If no recording
    exists for the date, raises FileNotFoundError.
    """
    stamp = date.replace('-', '')
    sym = config.SYMBOL.lower()
    src = os.path.join(data_dir, REC_DIR_NAME, f'{sym}_{stamp}.gz')
    if not os.path.exists(src):
        raise FileNotFoundError(f'no collector recording for {date}: {src}')

    cache = os.path.join(data_dir, 'hist', date)
    os.makedirs(cache, exist_ok=True)

    work = _copy_locked(src, cache)
    feed_npz = os.path.join(cache, 'feed.npz')
    data = convert_rec(work, feed_npz)
    os.remove(work)

    print(f'[{date}] converted {len(data)} events -> {feed_npz}')
    # The collector records incremental depth only (no REST snapshot); the L2
    # book is built from the stream. No initial snapshot is produced.
    return {'feed': feed_npz, 'snapshot': None}


def prepare_range(start: str, end: str, data_dir: str = config.DATA_DIR) -> list:
    """Converts collector recordings for the inclusive date range.

    Skips (with a log line) dates that have no recording. Returns the list of
    ``{'feed': path, 'snapshot': None}`` dicts for the dates found.
    """
    from datetime import date as _date, timedelta

    s = _date.fromisoformat(start)
    e = _date.fromisoformat(end)
    out = []
    d = s
    while d <= e:
        iso = d.isoformat()
        try:
            out.append(prepare_day(iso, data_dir))
        except FileNotFoundError as exc:
            print(f'[prepare] {iso} skipped: {exc}')
        except Exception as exc:
            print(f'[prepare] {iso} skipped: {type(exc).__name__}: {exc}')
        d += timedelta(days=1)
    return out
