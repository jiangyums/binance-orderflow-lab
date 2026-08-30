import traceback


class EventProcessor:
    """纯粹的消息处理者/调度者，不介入业务细节。

    职责只有两件事：
      1. 从 event_queue 接收生产者（orderbook/trade worker）的消息
      2. 按消息类型路由给对应的数据消费者（engine）

    消息协议（生产者 → processor → engine）：
      book_updated / trade_updated   数据就绪，engine 开始消费
      book_error   / trade_error     数据出错，engine 停掉对应消费分支

    注意：dispatch 路径上没有任何 await，engine 的处理方法是同步执行的，
    这是"无锁共享全局状态"安全条件的一半（另一半是单事件循环）。
    """

    def __init__(
        self,
        event_queue,
        engine,
    ):

        self.event_queue = event_queue

        #
        # 数据消费者（OrderFlowEngine），engine 是唯一业务入口
        #
        self.engine = engine

        #
        # 消息路由表：消息 type → engine 的处理方法
        #
        self.routes = {
            "book_updated": self.engine.on_book_updated,
            "trade_updated": self.engine.on_trade_updated,
            "book_error": self.engine.on_book_error,
            "trade_error": self.engine.on_trade_error,
        }

        self.running = True

    async def run(self):

        print("Event processor started")

        while self.running:

            try:

                event = await self.event_queue.get()

                self.dispatch(event)

            except Exception:

                print("EventProcessor error:")

                traceback.print_exc()

    def dispatch(self, event):

        handler = self.routes.get(event.get("type"))

        if handler is None:

            return

        handler(event)

    def stop(self):

        self.running = False

        #
        # 调度者最后一条消息：通知消费者停止工作
        #
        self.engine.stop()
