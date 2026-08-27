class TakerMakerRatio:
    """Windowed taker-flow vs resting maker-depth breakout.

    The maker wall (depth@100ms) only refreshes every 100ms, so all trades
    within that 100ms face the SAME wall. We therefore accumulate taker volume
    across the wall's whole life and, on each wall refresh, compare the
    accumulated taker flow to that wall -- not per-trade.

    Window length is anchored to the wall's refresh cadence (100ms), so there
    is no temporal mismatch: every trade counted faced exactly this wall.
    """

    def __init__(self):
        self.bid_depth = 0.0       # current resting wall (bid side)
        self.ask_depth = 0.0       # current resting wall (ask side)
        self.taker_buy_win = 0.0    # taker buy accumulated since last wall
        self.taker_sell_win = 0.0  # taker sell accumulated since last wall
        self.last = {"buy_breakout": 0.0, "sell_breakout": 0.0}

    def update_trade(self, timestamp, side, qty):
        if side == "BUY":
            self.taker_buy_win += qty
        else:
            self.taker_sell_win += qty
        return self.last

    def update_book(self, timestamp, bid_depth, ask_depth):
        # taker flow accumulated while the PREVIOUS wall was live:
        buy_breakout = (
            self.taker_buy_win / self.ask_depth if self.ask_depth > 0 else 0.0
        )
        sell_breakout = (
            self.taker_sell_win / self.bid_depth if self.bid_depth > 0 else 0.0
        )
        self.last = {"buy_breakout": buy_breakout, "sell_breakout": sell_breakout}
        # reset accumulator and adopt the new wall
        self.taker_buy_win = 0.0
        self.taker_sell_win = 0.0
        self.bid_depth = bid_depth
        self.ask_depth = ask_depth
        return self.last
