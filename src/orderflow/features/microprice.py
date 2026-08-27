class MicroPrice:

    @staticmethod
    def calculate(book):

        # 最优买价
        best_bid = max(book.bids.keys())

        # 最优卖价
        best_ask = min(book.asks.keys())

        # 对应数量
        bid_qty = book.bids[best_bid]
        ask_qty = book.asks[best_ask]

        total_qty = bid_qty + ask_qty

        if total_qty == 0:
            return (best_bid + best_ask) / 2

        microprice = (best_ask * bid_qty + best_bid * ask_qty) / total_qty

        return microprice
