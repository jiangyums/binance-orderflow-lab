class CVD:

    def __init__(self):

        self.value = 0.0
        self.buy_volume = 0.0
        self.sell_volume = 0.0


    def update(
        self,
        side,
        qty
    ):

        if side == "BUY":

            self.buy_volume += qty
            self.value += qty


        elif side == "SELL":

            self.sell_volume += qty
            self.value -= qty


        return self.value


    def snapshot(self):

        return {
            "cvd": self.value,
            "buy_volume": self.buy_volume,
            "sell_volume": self.sell_volume,
        }