import collections


class StreamValidator:

    """

    数据流校验器

    监控 depth / trade 事件的 T 字段（交易时间），检测：

        1. 间隔过大（数据流中断 / websocket 断连）
        2. 时间戳倒退（排序或加工错误）
        3. 间隔分布统计（确认正常间隔是几十毫秒）

    """

    def __init__(self, gap_warn_ms=3000, report_every=2000):

        self.gap_warn_ms = gap_warn_ms

        self.report_every = report_every

        self._last = {}                       # event_type -> last T

        self._stats = {}

        for t in ("depth", "trade"):

            self._stats[t] = {
                "count": 0,
                "total": 0.0,
                "min": None,
                "max": 0.0,
                "samples": collections.deque(maxlen=5000),
            }

    def check(self, event_type, timestamp):

        if event_type not in self._stats:

            return

        if timestamp is None:

            return

        s = self._stats[event_type]

        prev = self._last.get(event_type)

        if prev is not None:

            gap = timestamp - prev

            s["count"] += 1

            s["total"] += gap

            s["min"] = gap if s["min"] is None else min(s["min"], gap)

            s["max"] = max(s["max"], gap)

            s["samples"].append(gap)

            if gap > self.gap_warn_ms:

                print("[VALIDATOR] %s GAP %.1fs (prev=%d now=%d)"
                      % (event_type, gap / 1000.0, prev, timestamp))

            elif gap < 0:

                print("[VALIDATOR] %s BACKWARDS %d < %d"
                      % (event_type, timestamp, prev))

            if s["count"] % self.report_every == 0:

                self._report(event_type)

        self._last[event_type] = timestamp

    def _report(self, event_type):

        s = self._stats[event_type]

        samples = sorted(s["samples"])

        n = len(samples)

        if n == 0:

            return

        mean = s["total"] / s["count"]

        p = lambda q: samples[min(n - 1, int(q * n))]

        print("[VALIDATOR] %s intervals: n=%d mean=%.1fms "
              "p50=%d p90=%d p99=%d max=%d"
              % (event_type, s["count"], mean,
                 p(0.5), p(0.9), p(0.99), s["max"]))
