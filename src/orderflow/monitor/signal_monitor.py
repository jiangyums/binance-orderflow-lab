from collections import Counter, defaultdict
import time



class SignalMonitor:


    def __init__(
        self,
        interval=60
    ):

        #
        # 输出周期
        #
        self.interval = interval


        self.last_report = time.time()



        #
        # 信号数量
        #
        self.signal_count = Counter()



        #
        # strength区间
        #
        self.strength_bucket = Counter()



        #
        # 总strength
        #
        self.total_strength = 0.0



        #
        # 样本数量
        #
        self.samples = 0



        #
        # Phase 10.6.1
        #
        # reason统计
        #
        # {
        #   "LONG":{
        #       "Strong buy imbalance":10
        #   }
        # }
        #
        self.reason_count = defaultdict(
            Counter
        )



        #
        # reason strength累计
        #
        self.reason_strength = defaultdict(
            lambda: defaultdict(float)
        )



        #
        # reason样本数
        #
        self.reason_samples = defaultdict(
            lambda: defaultdict(int)
        )







    def update(
        self,
        signal
    ):


        if signal is None:

            return



        side = signal.side.value


        strength = float(
            signal.strength
        )


        reason = signal.reason



        #
        # signal统计
        #
        self.signal_count[side] += 1



        #
        # strength统计
        #
        self._update_strength_bucket(
            strength
        )



        self.total_strength += strength

        self.samples += 1




        #
        # Phase 10.6.1
        #
        # reason统计
        #
        self.reason_count[side][reason] += 1



        self.reason_strength[side][reason] += strength



        self.reason_samples[side][reason] += 1





        #
        # 定时输出
        #
        now = time.time()


        if now - self.last_report >= self.interval:

            self.report()

            self.reset()







    def _update_strength_bucket(
        self,
        strength
    ):


        if strength < 0.5:

            bucket = "0-0.5"


        elif strength < 1:

            bucket = "0.5-1"


        elif strength < 2:

            bucket = "1-2"


        else:

            bucket = ">2"



        self.strength_bucket[bucket] += 1







    def report(self):


        print(
            "\n========== Signal Monitor =========="
        )



        print(
            f"Window: {self.interval} seconds\n"
        )



        #
        # signal数量
        #
        print(
            "Signals:"
        )


        print(
            "----------------"
        )



        for side in [
            "LONG",
            "SHORT",
            "FLAT"
        ]:


            print(
                f"{side:<8}: {self.signal_count[side]}"
            )





        #
        # strength分布
        #
        print(
            "\nStrength:"
        )


        print(
            "----------------"
        )



        for bucket in [
            "0-0.5",
            "0.5-1",
            "1-2",
            ">2"
        ]:


            print(
                f"{bucket:<8}: {self.strength_bucket[bucket]}"
            )






        #
        # 平均strength
        #
        if self.samples:


            avg = (
                self.total_strength /
                self.samples
            )


        else:

            avg = 0




        print(
            "\nAverage strength:",
            round(avg, 3)
        )






        #
        # Phase 10.6.1
        #
        # Reason Breakdown
        #
        print(
            "\nReason Breakdown:"
        )


        print(
            "----------------"
        )



        for side in [
            "LONG",
            "SHORT"
        ]:


            print(
                f"\n{side}:"
            )


            if not self.reason_count[side]:

                print(
                    "  none"
                )

                continue



            for reason, count in (
                self.reason_count[side]
                .most_common()
            ):


                total_strength = (
                    self.reason_strength[side][reason]
                )


                samples = (
                    self.reason_samples[side][reason]
                )



                avg_strength = (

                    total_strength / samples

                    if samples

                    else 0

                )



                print(

                    f"  {reason:<25}"
                    f" count={count:<5}"
                    f" avg_strength={avg_strength:.3f}"

                )






        print(
            "\n====================================\n"
        )








    def reset(
        self
    ):


        self.signal_count.clear()



        self.strength_bucket.clear()



        self.total_strength = 0.0



        self.samples = 0




        self.reason_count.clear()



        self.reason_strength.clear()



        self.reason_samples.clear()



        self.last_report = time.time()