import asyncio
import heapq


class EventQueue:

    def __init__(self):

        self.queue = []

        self.lock = asyncio.Lock()

    async def put(self, event):

        async with self.lock:

            heapq.heappush(self.queue, (event["timestamp"], event))

    async def get(self):

        async with self.lock:

            if not self.queue:

                return None

            _, event = heapq.heappop(self.queue)

            return event

    def size(self):

        return len(self.queue)
