import time
import heapq


class EventBuffer:
    """
    Timestamp reorder buffer

    [已退役] 事件改为纯信号（数据回读全局 market_state）后，
    重排失去作用对象，EventProcessor 不再使用本类。保留文件供回溯。

    原用途：
    - 接收 websocket 到达的乱序事件
    - 按 Binance timestamp 排序
    - 延迟一小段时间释放稳定事件

    event格式（生产者消息，数据回读全局 market_state）:

    {
        "type": "book_updated" | "trade_updated"
                             | "book_error"   | "trade_error",
        "timestamp": 123456789
    }

    """

    def __init__(self, delay_ms=100):

        # 延迟窗口
        self.delay_ms = delay_ms

        # 最小堆
        #
        # (
        #   timestamp,
        #   sequence,
        #   event
        # )
        #
        # sequence 防止相同timestamp比较event
        #
        self.heap = []

        self.sequence = 0

        # 最新事件时间
        self.latest_timestamp = 0

    def push(self, event):

        timestamp = event["timestamp"]

        self.latest_timestamp = max(self.latest_timestamp, timestamp)

        heapq.heappush(self.heap, (timestamp, self.sequence, event))

        self.sequence += 1

    def pop_ready(self):
        """
        返回已经安全的事件

        例如:

        latest timestamp:
            10000

        delay:
            100

        那么释放:

            timestamp <= 9900

        """

        ready = []

        threshold = self.latest_timestamp - self.delay_ms

        while self.heap:

            timestamp, _, event = self.heap[0]

            if timestamp > threshold:

                break

            heapq.heappop(self.heap)

            ready.append(event)

        return ready

    def flush(self):
        """
        程序退出时释放剩余事件
        """

        result = []

        while self.heap:

            _, _, event = heapq.heappop(self.heap)

            result.append(event)

        return result

    def size(self):

        return len(self.heap)
