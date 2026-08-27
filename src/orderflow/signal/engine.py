from .trade_ofi_signal import TradeOFISignal


from .signal import Signal, SignalSide


class SignalEngine:
    """Adopts trade-OFI (CVD diff) as the sole directional signal.

    Trade-OFI has shown the strongest, most consistent directional edge across
    the long-run observation, so the previous OBI + book-OFI blend is replaced
    by a single trade-OFI driver. The downstream evaluator/statistics (which
    already compute realized return_1s/5s/10s and average_return) are unchanged.
    """

    def __init__(
        self,
        tofi_threshold=0.0,
        tofi_scale=1.0,
        tofi_mode="linear",
        tofi_rank_fn=None,
    ):
        self.tofi = TradeOFISignal(
            threshold=tofi_threshold,
            scale=tofi_scale,
            mode=tofi_mode,
            rank_fn=tofi_rank_fn,
        )

    def generate(self, feature):
        return self.tofi.generate(feature)
