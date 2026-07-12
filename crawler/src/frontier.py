from __future__ import annotations

import asyncio


class Frontier:
    """Single work queue.
    It assumes URLs passed to add() are already normalized. It handles deduplication of URLs."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._seen: set[str] = set()

    def add(self, url: str) -> None:
        if url in self._seen:
            return
        self._seen.add(url)
        self._queue.put_nowait(url)

    async def next(self) -> str:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

    def mark_visited(self, url: str) -> None:
        self._seen.add(url)

    async def join(self) -> None:
        await self._queue.join()