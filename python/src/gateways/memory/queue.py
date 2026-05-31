"""In-memory Queue adapter wrapping asyncio.Queue (generic over item type)."""

import asyncio


class InMemoryQueue[T]:
    """Single-process FIFO queue implementing the domain Queue[T] port."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[T] = asyncio.Queue()

    async def put(self, item: T) -> None:
        await self._queue.put(item)

    async def get(self) -> T:
        return await self._queue.get()
