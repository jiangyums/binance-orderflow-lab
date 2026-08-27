class OrderBookImbalance:

    @staticmethod
    def calculate(book, levels=1):

        bids = sorted(book.bids.items(), reverse=True)[:levels]

        asks = sorted(book.asks.items())[:levels]

        bid_volume = sum(qty for _, qty in bids)

        ask_volume = sum(qty for _, qty in asks)

        total = bid_volume + ask_volume

        if total == 0:
            return 0.0

        return (bid_volume - ask_volume) / total
