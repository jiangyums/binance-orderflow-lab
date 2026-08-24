from src.orderflow.features.imbalance import (
    OrderBookImbalance
)

from src.orderflow.features.microprice import (
    MicroPrice
)

from src.orderflow.features.ofi import (
    OrderFlowImbalance
)

from src.orderflow.features.cvd import (
    CVD
)



class OrderFlowEngine:
    """
    Order Flow Feature Engine


    输入:

        OrderBook event
        Trade event


    输出:

        {
            timestamp,

            mid,
            microprice,
            spread,

            obi1,
            obi5,
            obi10,

            ofi,

            trade_side,
            trade_price,
            trade_qty,

            cvd
        }

    """



    def __init__(self):


        self.last_timestamp = None


        #
        # trade状态
        #

        self.last_trade = {

            "side": None,

            "price": None,

            "qty": 0

        }


        #
        # CVD
        #

        self.cvd = CVD()



        #
        # OFI
        #

        self.ofi = OrderFlowImbalance()



        #
        # 最近orderbook
        #

        self.order_book = None



        #
        # 当前feature
        #

        self.feature = None




    def update_book(
        self,
        order_book,
        timestamp
    ):


        self.order_book = order_book


        self.last_timestamp = timestamp



        #
        # OBI
        #

        obi1 = (
            OrderBookImbalance.calculate(
                order_book,
                levels=1
            )
        )


        obi5 = (
            OrderBookImbalance.calculate(
                order_book,
                levels=5
            )
        )


        obi10 = (
            OrderBookImbalance.calculate(
                order_book,
                levels=10
            )
        )



        #
        # MicroPrice
        #

        micro = (
            MicroPrice.calculate(
                order_book
            )
        )


        #
        # mid / spread
        #

        bid = order_book.best_bid()

        ask = order_book.best_ask()


        if bid is None or ask is None:

            return None



        mid = (
            bid + ask
        ) / 2


        spread = (
            ask - bid
        )



        #
        # OFI
        #

        ofi_value = (

            self.ofi.update(

                order_book

            )

        )



        self.feature = {


            "timestamp":
                timestamp,


            "mid":
                mid,


            "microprice":
                micro,


            "spread":
                spread,


            "obi1":
                obi1,


            "obi5":
                obi5,


            "obi10":
                obi10,


            "ofi":
                ofi_value,


            "trade_side":
                self.last_trade["side"],


            "trade_price":
                self.last_trade["price"],


            "trade_qty":
                self.last_trade["qty"],


            "cvd":
                self.cvd.value

        }



        return self.feature





    def update_trade(
        self,
        price,
        qty,
        side,
        timestamp
    ):


        self.last_timestamp = timestamp



        self.last_trade = {


            "side":
                side,


            "price":
                price,


            "qty":
                qty

        }



        #
        # 更新CVD
        #

        self.cvd.update(
            side,
            qty
        )

        if self.feature is not None:
            self.feature["timestamp"] = timestamp
            self.feature["trade_side"] = side
            self.feature["trade_price"] = price
            self.feature["trade_qty"] = qty
            self.feature["cvd"] = self.cvd.value

        return self.feature





    def snapshot(self):

        return self.feature