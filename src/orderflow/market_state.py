"""
全局市场状态：orderbook 与 tradeSet

数据流（单进程 asyncio）：
  - binance_depth 在快照+增量流合并成功后，原地更新全局 orderbook，
    之后每收到一条流数据，只对外发出一个 book_updated 信号
    （事件不再携带订单簿副本）。
  - binance_trade 每收到一笔成交，追加到全局 trade_set，
    并发出 trade_updated 信号。
  - event_processor 看到信号后，回读本模块的全局变量计算指标。

写入方（collector 协程）与读取方（processor 协程）运行在同一个事件循环，
不跨 await 的单次读写天然原子，无需加锁。
"""

from collections import deque

import time

import aiohttp

from src.orderflow.book.order_book import OrderBook


SERVER_TIME_URL = "https://fapi.binance.com/fapi/v1/time"


#
# 服务器时钟偏移（ms）：服务器时间 ≈ 本机时间 + clock_offset_ms。
# 启动时由 calibrate_clock() 校准；校准失败保持 0（退化为本机时钟）。
#
clock_offset_ms = 0.0


async def calibrate_clock(samples=3, session=None):
    """请求 /fapi/v1/time 校准时钟偏移。

    单次请求的精度受往返时延影响，按 NTP 思路估计：
        偏移 = serverTime - (发送时刻 + 接收时刻) / 2
    采样多次取 RTT 最小的一次（路径抖动最小的样本最可信）。

    session 参数供测试注入假会话；不传则自建并负责关闭。
    校准失败不致命：打印警告，偏移保持原值。
    """

    global clock_offset_ms

    own_session = session is None

    if own_session:

        session = aiohttp.ClientSession()

    try:

        best = None  # (rtt, offset)

        for _ in range(samples):

            t0 = time.time() * 1000

            async with session.get(SERVER_TIME_URL) as resp:

                resp.raise_for_status()

                data = await resp.json()

            t1 = time.time() * 1000

            rtt = t1 - t0

            offset = data["serverTime"] - (t0 + t1) / 2

            if best is None or rtt < best[0]:

                best = (rtt, offset)

        clock_offset_ms = best[1]

        print(
            f"[clock] 校准完成：服务器比本机快 {clock_offset_ms:+.0f}ms "
            f"（采样 RTT {best[0]:.0f}ms）"
        )

        return clock_offset_ms

    except Exception as exc:

        print(
            f"[clock] 校准失败（{type(exc).__name__}: {exc}），"
            "继续使用本机时钟"
        )

        return clock_offset_ms

    finally:

        if own_session:

            await session.close()


def now_ms():
    """校准后的当前时间（服务器时间轴，ms），所有延迟计算统一用它。"""

    return time.time() * 1000 + clock_offset_ms


#
# 延迟丢弃阈值（ms）：数据时间戳与本机时间的差超过该值视为过期。
# depth 100ms 推送周期等正常链路总滞后 <200ms，
# 1s 以上的滞后说明网络/机器严重落后。
#
LATENCY_MAX_MS = 1000


#
# 丢弃日志限频：同一秒内多条丢弃只打一条，避免高丢包时刷屏
#
_last_drop_log = 0.0


def log_stale_drop(stream, latency_ms):
    """生产者/消费者丢弃过期数据时的统一限频日志。"""

    global _last_drop_log

    now = time.time()

    if now - _last_drop_log >= 1.0:

        _last_drop_log = now

        print(f"[latency] {stream} 数据滞后 {latency_ms}ms "
              f"(> {LATENCY_MAX_MS}ms)，丢弃")


#
# 全局订单簿：depth 协程唯一写入，processor 只读
#
orderbook = OrderBook()


#
# 快照+流是否已成功合并；合并成功之前 processor 忽略 book_updated 信号
#
book_ready = False


#
# 全局成交集合（tradeSet）：每笔 {"timestamp", "price", "qty", "side"}。
# trade 协程追加，processor 消费时 popleft。
# maxlen 兜底：processor 长时间停滞时丢最旧的成交，防止内存无限增长
#
trade_set = deque(maxlen=100000)
