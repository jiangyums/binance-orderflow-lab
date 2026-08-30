import csv
import os
from collections import deque


class SignalEvaluator:

    def __init__(self, filename="data/evaluation.csv"):

        directory = os.path.dirname(filename)

        if directory:

            os.makedirs(directory, exist_ok=True)

        self.file = open(filename, "w", newline="", encoding="utf-8")

        self.writer = csv.DictWriter(
            self.file,
            fieldnames=[
                "signal_time",
                "signal",
                "strength",
                "entry_price",
                "return_1s",
                "return_5s",
                "return_10s",
            ],
        )

        self.writer.writeheader()

        #
        # 等待中的signal
        #
        self.pending = deque()

        #
        # 最近价格
        #
        self.prices = deque(maxlen=2000)

    def add_signal(self, signal, feature, entry_mid=None):

        self.pending.append(
            {
                "timestamp": signal.timestamp,
                "signal": signal.side.value,
                "strength": signal.strength,
                "price": entry_mid if entry_mid is not None else feature["mid"],
            }
        )

    def update_price(self, timestamp, price):

        self.prices.append((timestamp, price))

        finished = []

        for item in list(self.pending):

            t0 = item["timestamp"]

            future = {}

            for t, p in self.prices:

                diff = t - t0

                if diff >= 1000 and "1s" not in future:

                    future["1s"] = p

                if diff >= 5000 and "5s" not in future:

                    future["5s"] = p

                if diff >= 10000 and "10s" not in future:

                    future["10s"] = p

            if len(future) == 3:

                entry = item["price"]

                self.writer.writerow(
                    {
                        "signal_time": t0,
                        "signal": item["signal"],
                        "strength": item["strength"],
                        "entry_price": entry,
                        "return_1s": (future["1s"] - entry) / entry,
                        "return_5s": (future["5s"] - entry) / entry,
                        "return_10s": (future["10s"] - entry) / entry,
                    }
                )

                self.file.flush()

                finished.append(item)

        for item in finished:

            self.pending.remove(item)

    def close(self):

        self.file.close()
