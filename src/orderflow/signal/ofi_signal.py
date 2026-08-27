from .signal import Signal, SignalSide


class OFISignal:
    def __init__(self, threshold=1.0, scale=10.0, mode="linear", rank_fn=None):
        self.threshold = threshold
        self.scale = scale
        self.mode = mode
        self.rank_fn = rank_fn

    def _strength(self, ofi):
        mag = abs(ofi)
        if self.mode == "rank" and self.rank_fn is not None:
            return max(0.0, min(1.0, self.rank_fn(mag)))
        return min(mag / self.scale, 1.0)

    def generate(self, feature):
        ofi = feature["ofi"]

        #
        # 正OFI：买方主动流增强
        #
        if ofi > self.threshold:
            return Signal(
                feature["timestamp"], SignalSide.LONG, self._strength(ofi), "Positive OFI"
            )

        #
        # 负OFI：卖方主动流增强
        #
        elif ofi < -self.threshold:
            return Signal(
                feature["timestamp"],
                SignalSide.SHORT,
                self._strength(ofi),
                "Negative OFI",
            )

        return Signal(feature["timestamp"], SignalSide.FLAT, 0, "Neutral OFI")
