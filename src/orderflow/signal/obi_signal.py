from .signal import Signal, SignalSide


class OBISignal:

    def __init__(self, threshold=0.6):

        self.threshold = threshold

    def generate(self, feature):

        obi = feature["obi5"]

        #
        # 买方挂单优势
        #
        if obi > self.threshold:

            return Signal(
                feature["timestamp"], SignalSide.LONG, abs(obi), "Strong buy imbalance"
            )

        #
        # 卖方挂单优势
        #
        elif obi < -self.threshold:

            return Signal(
                feature["timestamp"],
                SignalSide.SHORT,
                abs(obi),
                "Strong sell imbalance",
            )

        return Signal(feature["timestamp"], SignalSide.FLAT, 0, "No imbalance")
