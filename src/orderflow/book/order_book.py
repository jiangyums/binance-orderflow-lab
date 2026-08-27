from decimal import Decimal


class OrderBook:
    """
    Binance Futures L2 Order Book

    bids:
        price -> quantity

    asks:
        price -> quantity

    price 使用 float
    quantity 使用 float

    """

    def __init__(self):

        self.bids = {}

        self.asks = {}

        self.last_update_id = None

    def load_snapshot(self, snapshot):
        """
        Binance REST snapshot

        {
            lastUpdateId: xxx,
            bids:[
                ["price","qty"]
            ],
            asks:[
                ["price","qty"]
            ]
        }

        """

        self.bids.clear()

        self.asks.clear()

        for price, qty in snapshot["bids"]:

            price = float(price)

            qty = float(qty)

            if qty > 0:

                self.bids[price] = qty

        for price, qty in snapshot["asks"]:

            price = float(price)

            qty = float(qty)

            if qty > 0:

                self.asks[price] = qty

        self.last_update_id = snapshot["lastUpdateId"]

    def apply_update(self, event):
        """
        Binance depthUpdate

        b:
        [
          [price, qty]
        ]

        a:
        [
          [price, qty]
        ]

        """

        #
        # bids update
        #

        for price, qty in event["b"]:

            price = float(price)

            qty = float(qty)

            if qty == 0:

                self.bids.pop(price, None)

            else:

                self.bids[price] = qty

        #
        # asks update
        #

        for price, qty in event["a"]:

            price = float(price)

            qty = float(qty)

            if qty == 0:

                self.asks.pop(price, None)

            else:

                self.asks[price] = qty

        self.last_update_id = event["u"]

    #
    # ======================
    # Best Bid / Ask
    # ======================
    #

    def best_bid(self):

        if not self.bids:

            return None

        return max(self.bids.keys())

    def best_ask(self):

        if not self.asks:

            return None

        return min(self.asks.keys())

    #
    # ======================
    # Volume
    # ======================
    #

    def bid_volume(self, price):

        return self.bids.get(price, 0)

    def ask_volume(self, price):

        return self.asks.get(price, 0)

    #
    # ======================
    # Market features
    # ======================
    #

    def mid_price(self):

        bid = self.best_bid()

        ask = self.best_ask()

        if bid is None:

            return None

        if ask is None:

            return None

        return (bid + ask) / 2

    def spread(self):

        bid = self.best_bid()

        ask = self.best_ask()

        if bid is None:

            return None

        if ask is None:

            return None

        return ask - bid

    #
    # ======================
    # Depth levels
    # ======================
    #

    def get_bid_levels(self, levels=10):

        return sorted(self.bids.items(), key=lambda x: x[0], reverse=True)[:levels]

    def get_ask_levels(self, levels=10):

        return sorted(self.asks.items(), key=lambda x: x[0])[:levels]

    #
    # ======================
    # Debug
    # ======================
    #

    def __len__(self):

        return len(self.bids) + len(self.asks)

    def info(self):

        return {
            "bids": len(self.bids),
            "asks": len(self.asks),
            "best_bid": self.best_bid(),
            "best_ask": self.best_ask(),
            "spread": self.spread(),
            "mid": self.mid_price(),
            "update_id": self.last_update_id,
        }

    def copy(self):

        new_book = OrderBook()

        new_book.bids = dict(self.bids)

        new_book.asks = dict(self.asks)

        new_book.last_update_id = self.last_update_id

        return new_book
