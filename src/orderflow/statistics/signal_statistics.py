import csv
from collections import defaultdict



class SignalStatistics:


    def __init__(self):


        self.data = []



    def load(
        self,
        filename
    ):


        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:


            reader = csv.DictReader(
                f
            )


            for row in reader:


                row["strength"] = float(
                    row["strength"]
                )


                row["return_1s"] = float(
                    row["return_1s"]
                )


                row["return_5s"] = float(
                    row["return_5s"]
                )


                row["return_10s"] = float(
                    row["return_10s"]
                )


                self.data.append(
                    row
                )



    def win_rate(
        self,
        signal,
        horizon="return_5s"
    ):


        samples = [

            x for x in self.data

            if x["signal"] == signal

        ]



        if not samples:

            return 0



        wins = 0



        for x in samples:


            ret = x[horizon]



            if signal == "LONG":


                if ret > 0:

                    wins += 1



            elif signal == "SHORT":


                if ret < 0:

                    wins += 1



        return wins / len(samples)




    def _pnl(
        self,
        row,
        horizon
    ):
        ret = row[horizon]
        return ret if row["signal"] == "LONG" else -ret


    def average_return(
        self,
        signal,
        horizon="return_5s"
    ):


        samples = [

            self._pnl(x, horizon)

            for x in self.data

            if x["signal"] == signal

        ]



        if not samples:

            return 0



        return sum(samples) / len(samples)




    def strength_bucket(self):


        result = defaultdict(list)



        for x in self.data:


            s = x["strength"]



            if s < 0.5:

                bucket = "0-0.5"


            elif s < 1:

                bucket = "0.5-1"


            elif s < 2:

                bucket = "1-2"


            else:

                bucket = ">2"



            result[bucket].append(
                x
            )



        return result




    def report(self):


        print(
            "\n===== Signal Statistics ====="
        )


        for signal in [

            "LONG",
            "SHORT"

        ]:

            samples = [

                x for x in self.data
                if x["signal"] == signal

            ]

            print(
                "samples:",
                len(samples)
            )

            for horizon in [

                "return_1s",
                "return_5s",
                "return_10s"

            ]:

                print(
                    f"  {horizon}: "
                    f"win={round(self.win_rate(signal, horizon), 3)} "
                    f"avg_ret={round(self.average_return(signal, horizon), 5)}"
                )


        print(
            "\n===== By Strength Bucket ====="
        )


        buckets = self.strength_bucket()


        for bucket in [

            "0-0.5",
            "0.5-1",
            "1-2",
            ">2"

        ]:

            items = [
                x for x in buckets.get(bucket, [])
                if x["signal"] in ("LONG", "SHORT")
            ]

            if not items:

                print(
                    f"\n  {bucket}: (no samples)"
                )

                continue

            print(
                f"\n  {bucket} (n={len(items)})"
            )

            for horizon in [

                "return_1s",
                "return_5s",
                "return_10s"

            ]:

                wins = sum(

                    1
                    for x in items
                    if (
                        (
                            x["signal"] == "LONG"
                            and x[horizon] > 0
                        )
                        or
                        (
                            x["signal"] == "SHORT"
                            and x[horizon] < 0
                        )
                    )

                )

                avg = (
                    sum(
                        self._pnl(x, horizon)
                        for x in items
                    )
                    / len(items)
                )

                print(
                    f"    {horizon}: "
                    f"win={round(wins / len(items), 3)} "
                    f"avg_ret={round(avg, 5)}"
                )
