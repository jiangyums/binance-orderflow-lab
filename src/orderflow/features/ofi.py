class OrderFlowImbalance:

    def __init__(self):

        self.last_bid_price = None
        self.last_ask_price = None

        self.last_bid_size = 0
        self.last_ask_size = 0

        self.ofi = 0

    def update(self, order_book):

        if not order_book.bids:
            return 0

        if not order_book.asks:
            return 0

        bid_price = max(order_book.bids.keys())

        ask_price = min(order_book.asks.keys())

        bid_size = order_book.bids[bid_price]

        ask_size = order_book.asks[ask_price]

        if self.last_bid_price is None:

            self.last_bid_price = bid_price
            self.last_ask_price = ask_price

            self.last_bid_size = bid_size
            self.last_ask_size = ask_size

            return 0

        ofi = 0

        if bid_price > self.last_bid_price:

            ofi += bid_size

        elif bid_price == self.last_bid_price:

            ofi += bid_size - self.last_bid_size

        if ask_price < self.last_ask_price:

            ofi -= ask_size

        elif ask_price == self.last_ask_price:

            ofi -= ask_size - self.last_ask_size

        self.last_bid_price = bid_price
        self.last_ask_price = ask_price

        self.last_bid_size = bid_size
        self.last_ask_size = ask_size

        self.ofi = ofi

        return ofi
