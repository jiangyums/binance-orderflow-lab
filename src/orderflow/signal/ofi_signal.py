from .signal import (
    Signal,
    SignalSide
)


class OFISignal:


    def __init__(
        self,
        threshold=1.0
    ):

        self.threshold = threshold



    def generate(
        self,
        feature
    ):

        ofi = feature["ofi"]



        #
        # 正OFI：买方主动流增强
        #
        if ofi > self.threshold:

            return Signal(

                feature["timestamp"],

                SignalSide.LONG,

                min(ofi / 10, 1),

                "Positive OFI"

            )



        #
        # 负OFI：卖方主动流增强
        #
        elif ofi < -self.threshold:

            return Signal(

                feature["timestamp"],

                SignalSide.SHORT,

                min(abs(ofi) / 10, 1),

                "Negative OFI"

            )



        return Signal(

            feature["timestamp"],

            SignalSide.FLAT,

            0,

            "Neutral OFI"

        )