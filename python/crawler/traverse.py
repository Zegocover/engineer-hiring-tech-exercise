import logging
from asyncio import Queue, CancelledError, TaskGroup
from collections import deque
from typing import Awaitable, Callable, TypeVar, List, Set, Generic, Deque


logger = logging.getLogger(__name__)


T = TypeVar("T")


class PooledTraverse(Generic[T]):
    def __init__(
        self,
        root: T,
        visit: Callable[[T], Awaitable[List[T]]],
        workers: int,
    ) -> None:
        self._root = root
        self._visit = visit
        self._workers = workers

        self._queue: Queue[T] = Queue()
        self._visited: Set[T] = set()

    async def run(self) -> List[T]:
        self._visited.add(self._root)
        await self._queue.put(self._root)

        # Using a TaskGroup and a separate job task ensures:
        # 1. No deadlocks if a worker dies
        # 2. The class fails fast, does not have to match each _queue.put with a _queue.task_done
        async with TaskGroup() as pool:
            workers = [pool.create_task(self._worker(i+1)) for i in range(self._workers)]

            async def job() -> None:
                logger.debug(f'Job task started')
                try:
                    await self._queue.join()
                    for w in workers:
                        w.cancel()

                except CancelledError:
                    logger.debug(f'Job task shutdown')

            pool.create_task(job())

        return list(self._visited)

    async def _worker(self, i: int) -> None:
        logger.debug(f"Worker task {i} started")

        try:
            while True:
                node = await self._queue.get()

                neighbors = await self._visit(node)
                for neighbor in neighbors:
                    if neighbor not in self._visited:
                        self._visited.add(neighbor)
                        await self._queue.put(neighbor)

                self._queue.task_done()

        except CancelledError:
            logger.debug(f'Worker task {i} shutdown')


class BFSTraverse(Generic[T]):
    def __init__(
        self,
        root: T,
        visit: Callable[[T], Awaitable[List[T]]],
        workers: int = 1,
    ) -> None:
        self._root = root
        self._visit = visit

        self._queue: Deque[T] = deque()
        self._visited: Set[T] = set()

    async def run(self) -> List[T]:
        self._visited.add(self._root)
        self._queue.append(self._root)

        while self._queue:
            node = self._queue.popleft()

            neighbors = await self._visit(node)
            for neighbor in neighbors:
                if neighbor not in self._visited:
                    self._visited.add(neighbor)
                    self._queue.append(neighbor)

        return list(self._visited)
