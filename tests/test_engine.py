from src.orderflow.book.order_book import OrderBook

from src.orderflow.engine import OrderFlowEngine


engine = OrderFlowEngine()


order_book = OrderBook()

order_book.load_snapshot(
    {
        "lastUpdateId": 100,
        "bids": [
            ["77300.0", "1.0"],
            ["77299.0", "2.0"],
        ],
        "asks": [
            ["77300.1", "1.5"],
            ["77300.2", "2.5"],
        ],
    }
)


engine.update_book(
    order_book,
    timestamp=123456
)


engine.update_trade(
    price=77300.1,
    qty=1.5,
    side="BUY",
    timestamp=123457
)


print(
    engine.snapshot()
)
