from .signal import Signal, SignalSide


class TradeOFISignal:
    """Signal driven by trade-OFI (CVD diff / net taker flow per trade).

    Positive trade-OFI -> net buying pressure -> LONG.
    Negative trade-OFI -> net selling pressure -> SHORT.
    Magnitude (strength) is the abs(trade-OFI) scaled into [0, 1] for the
    strength-bucket analysis; the directional edge lives in the sign.
    """

    def __init__(self, threshold=0.0, scale=1.0, mode="linear", rank_fn=None):
        self.threshold = threshold
        self.scale = scale
        self.mode = mode
        self.rank_fn = rank_fn

    def _strength(self, tofi):
        mag = abs(tofi)
        if self.mode == "rank" and self.rank_fn is not None:
            return max(0.0, min(1.0, self.rank_fn(mag)))
        return min(mag / self.scale, 1.0)

    def generate(self, feature):
        tofi = feature.get("tofi") or 0.0

        if tofi > self.threshold:
            return Signal(
                feature["timestamp"],
                SignalSide.LONG,
                self._strength(tofi),
                "Positive trade-OFI",
            )

        if tofi < -self.threshold:
            return Signal(
                feature["timestamp"],
                SignalSide.SHORT,
                self._strength(tofi),
                "Negative trade-OFI",
            )

        return Signal(feature["timestamp"], SignalSide.FLAT, 0, "Neutral trade-OFI")
