import asyncio
import json
import os
import time
import websockets


SYMBOL = "btcusdt"
TRADE_WS = f"wss://fstream.binance.com/ws/{SYMBOL}@trade"
AGG_WS = f"wss://fstream.binance.com/market/ws/{SYMBOL}@aggTrade"
DURATION = 60.0
OUT_DIR = "data"


def _bucket_stats(ts_list, width_ms=100):
    buckets = {}
    for t in ts_list:
        b = int(t) // width_ms
        buckets[b] = buckets.get(b, 0) + 1
    counts = list(buckets.values())
    return (
        max(counts) if counts else 0,
        sum(counts) / len(counts) if counts else 0,
        len(buckets),
    )


async def _collect_one(url, sink):
    start = time.time()
    try:
        async with websockets.connect(url, ping_interval=None) as ws:
            while time.time() - start < DURATION:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5)
                except asyncio.TimeoutError:
                    continue
                sink.append((time.time(), json.loads(msg)))
    except Exception as e:
        print(f"  [warn] {url} -> {type(e).__name__}: {e}")


async def collect():
    raw_trade = []
    raw_agg = []
    await asyncio.gather(
        _collect_one(TRADE_WS, raw_trade),
        _collect_one(AGG_WS, raw_agg),
    )
    return raw_trade, raw_agg


def analyze(raw_trade, raw_agg):
    t_t = [float(d["T"]) for _, d in raw_trade]
    a_t = [float(d["T"]) for _, d in raw_agg]

    sum_t = sum(float(d["q"]) for _, d in raw_trade)
    sum_a = sum(float(d["q"]) for _, d in raw_agg)

    def cvd(rows):
        s = 0.0
        for _, d in rows:
            q = float(d["q"])
            s += q if not d["m"] else -q
        return s

    cvd_t = cvd(raw_trade)
    cvd_a = cvd(raw_agg)

    print("=" * 60)
    print("A. 消息节奏")
    print("-" * 60)
    print(f"  @trade   : {len(raw_trade):>7d} 条  (~{len(raw_trade)/DURATION:.1f}/s)")
    print(f"  @aggTrade: {len(raw_agg):>7d} 条  (~{len(raw_agg)/DURATION:.1f}/s)")
    if len(t_t) > 1:
        ts = sorted(t_t)
        diffs = [ts[i] - ts[i - 1] for i in range(1, len(ts))]
        under = sum(1 for d in diffs if d < 100)
        print(f"  @trade 相邻T间隔: min={min(diffs):.1f} median="
              f"{sorted(diffs)[len(diffs)//2]:.1f} max={max(diffs):.1f}ms")
        print(f"  @trade 间隔<100ms占比: {under/len(diffs)*100:.1f}%")
    mt_max, _, mt_n = _bucket_stats(t_t)
    ma_max, _, ma_n = _bucket_stats(a_t)
    print(f"  @trade   每100ms桶最多 {mt_max} 条 (桶数 {mt_n})")
    print(f"  @aggTrade每100ms桶最多 {ma_max} 条 (桶数 {ma_n})  -> 聚合后每桶极少")

    print("=" * 60)
    print("B. 成交量守恒 (同批成交两种分组, Σq 应相等)")
    print("-" * 60)
    print(f"  Σq @trade   = {sum_t:.6f}")
    print(f"  Σq @aggTrade= {sum_a:.6f}")
    diff = abs(sum_t - sum_a)
    print(f"  差 = {diff:.6f}  ({'PASS' if diff < 0.001*max(sum_t,1) else 'CHECK'})")

    print("=" * 60)
    print("C. taker 方向一致性 (按 m 算 CVD, 两流应一致)")
    print("-" * 60)
    print(f"  CVD @trade   = {cvd_t:+.6f}")
    print(f"  CVD @aggTrade= {cvd_a:+.6f}")
    diff = abs(cvd_t - cvd_a)
    print(f"  差 = {diff:.6f}  ({'PASS' if diff < 0.001*max(abs(cvd_t),1) else 'CHECK'})")

    print("=" * 60)
    print("D. 字段核对")
    print("-" * 60)
    if raw_trade:
        print(f"  @trade   字段: {sorted(raw_trade[0][1].keys())}")
    if raw_agg:
        print(f"  @aggTrade字段: {sorted(raw_agg[0][1].keys())}")

    print("=" * 60)
    print("E. 样本 (前3条)")
    print("-" * 60)
    for i in range(min(3, len(raw_trade))):
        print(f"  @trade   [{i}]: {json.dumps(raw_trade[i][1], ensure_ascii=False)}")
    for i in range(min(3, len(raw_agg))):
        print(f"  @aggTrade[{i}]: {json.dumps(raw_agg[i][1], ensure_ascii=False)}")

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"verify_trade_{int(time.time())}.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for _, d in raw_trade:
            f.write(json.dumps({"stream": "trade", "data": d}) + "\n")
        for _, d in raw_agg:
            f.write(json.dumps({"stream": "aggTrade", "data": d}) + "\n")
    print(f"\n原始数据已存: {out}")


async def main():
    print(f"@trade   : {TRADE_WS}")
    print(f"@aggTrade: {AGG_WS}")
    print(f"采集 {DURATION}s ...\n")
    raw_trade, raw_agg = await collect()
    analyze(raw_trade, raw_agg)


if __name__ == "__main__":
    asyncio.run(main())
