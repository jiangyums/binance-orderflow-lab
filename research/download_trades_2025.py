"""Download 2025-01 aggTrades (BTCUSDT) for 30-day VPIN evaluation.

Covers 2025-01-01 .. 2025-01-31 from data.binance.vision.
Skips already-valid zips (testzip() == None), validates after download,
deletes corrupted files and retries once. Consistent with vpin_validity.py:98-105.
"""
import zipfile
import sys
from pathlib import Path
from datetime import date, timedelta

try:
    import requests
except ImportError:
    requests = None

BASE = Path("data/hist/trades")
BASE.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://data.binance.vision/data/spot/daily/trades/BTCUSDT/BTCUSDT-trades-{d}.zip"


def is_valid_zip(path: Path) -> bool:
    """Return True iff path exists and zipfile.testzip() == None (no bad file)."""
    if not path.exists():
        return False
    try:
        with zipfile.ZipFile(str(path)) as zf:
            # testzip returns None if no errors, else name of first bad file
            bad = zf.testzip()
            return bad is None
    except Exception:
        return False


def count_trades(path: Path) -> int:
    """Count trades (lines excluding header) inside zip. Returns 0 on error."""
    try:
        with zipfile.ZipFile(str(path)) as zf:
            name = zf.namelist()[0]
            with zf.open(name) as f:
                raw = f.read().decode("utf-8", errors="ignore")
            # header + rows
            lines = [l for l in raw.split("\n") if l.strip()]
            return max(0, len(lines) - 1)
    except Exception:
        return 0


def download_one(d: str, retries: int = 1) -> bool:
    """Download single date d (YYYY-MM-DD). Returns True if saved & valid."""
    url = BASE_URL.format(d=d)
    out = BASE / f"BTCUSDT-trades-{d}.zip"

    # Skip valid existing
    if out.exists():
        if is_valid_zip(out):
            n = count_trades(out)
            print(f"Skip (valid): {d} ({n} trades) - {out.name}")
            return True
        else:
            print(f"Corrupted existing, re-downloading: {d} ({out.name})", flush=True)
            try:
                out.unlink()
            except Exception:
                pass

    if requests is None:
        print(f"FAIL {d}: requests not installed", flush=True)
        return False

    for attempt in range(retries + 1):
        try:
            print(f"Downloading {d}... (attempt {attempt+1}/{retries+1})", end=" ", flush=True)
            r = requests.get(url, timeout=120)
            if r.status_code != 200:
                print(f"FAIL ({r.status_code}) {url}", flush=True)
                if r.status_code in (404, 451):
                    # Not found or blocked — don't retry indefinitely
                    if r.status_code == 451 and attempt == 0 and retries >= 1:
                        continue
                if attempt < retries:
                    continue
                return False
            out.write_bytes(r.content)
            # Validate
            if is_valid_zip(out):
                n = count_trades(out)
                print(f"Saved: {out} ({n} trades)", flush=True)
                return True
            else:
                print(f"FAIL (corrupted zip) {d}", flush=True)
                try:
                    out.unlink()
                except Exception:
                    pass
                if attempt < retries:
                    print(f"  Retrying {d}...", flush=True)
                    continue
                return False
        except Exception as e:
            print(f"FAIL ({e}) {d}", flush=True)
            try:
                if out.exists():
                    out.unlink()
            except Exception:
                pass
            if attempt < retries:
                print(f"  Retrying {d}...", flush=True)
                continue
            return False
    return False


def main(start: str = "2025-01-01", end: str = "2025-01-31"):
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    cur = s
    total = 0
    ok = 0
    while cur <= e:
        d = cur.isoformat()
        total += 1
        if download_one(d, retries=1):
            ok += 1
        cur += timedelta(days=1)
    print(f"\nDone: {ok}/{total} valid zips in {BASE}", flush=True)
    # Summary valid count
    valid = sum(1 for z in BASE.glob("BTCUSDT-trades-2025-*.zip") if is_valid_zip(z))
    print(f"Valid 2025 zips on disk: {valid}", flush=True)


if __name__ == "__main__":
    # Allow optional CLI args: start end
    if len(sys.argv) >= 3:
        main(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2:
        main(sys.argv[1], "2025-01-31")
    else:
        main()
