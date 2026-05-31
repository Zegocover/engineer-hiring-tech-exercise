"""The crawl coordinator: N fetch workers + a single parse loop, joined by two
queues. Owns the visited set and in-flight counter; detects completion when
in_flight reaches zero. Public API is an async iterator of PageResult."""

import asyncio
from collections.abc import AsyncIterator

from domains.crawler.models import CrawlConfig, FetchResult, PageResult
from domains.crawler.ports import FetchStage, ParseStage, Queue


class Crawler:
    """Single-domain crawler. The `crawl` loop (this coroutine) is the only
    writer of `_visited` and `_in_flight`, so no locks are needed.

    Shutdown uses task cancellation, not a sentinel: when `_in_flight` reaches 0
    every enqueued URL has been fetched AND parsed, so all workers are guaranteed
    idle (blocked on `frontier.get()`) and can be cancelled safely. This keeps
    the queues cleanly typed (`Queue[str]` / `Queue[FetchResult]`).
    """

    def __init__(
        self,
        config: CrawlConfig,
        fetch_stage: FetchStage,
        parse_stage: ParseStage,
        frontier: Queue[str],
        results: Queue[FetchResult],
    ) -> None:
        self._config = config
        self._fetch_stage = fetch_stage
        self._parse_stage = parse_stage
        self._frontier = frontier
        self._results = results
        self._visited: set[str] = set()
        self._in_flight = 0
        self._truncated = False

    async def crawl(self) -> AsyncIterator[PageResult]:
        await self._enqueue(self._config.seed_url)
        workers = self._spawn_workers()
        try:
            while self._in_flight > 0:
                yield await self._process_one()
        finally:
            await self._stop_workers(workers)

    async def _process_one(self) -> PageResult:
        result = await self._results.get()
        outcome = await self._parse_stage.parse(result)
        for url in outcome.on_host_links:
            await self._enqueue_if_new(url)
        self._in_flight -= 1
        return outcome.page

    async def _enqueue_if_new(self, url: str) -> None:
        if url in self._visited:
            return
        if self._at_cap:
            self._truncated = True
            return
        await self._enqueue(url)

    async def _enqueue(self, url: str) -> None:
        # The only writer of _visited / _in_flight.
        self._visited.add(url)
        self._in_flight += 1
        await self._frontier.put(url)

    @property
    def _at_cap(self) -> bool:
        cap = self._config.max_pages
        return cap is not None and len(self._visited) >= cap

    @property
    def truncated(self) -> bool:
        """True if --max-pages stopped the crawl short of completion."""
        return self._truncated

    def _spawn_workers(self) -> list[asyncio.Task[None]]:
        return [asyncio.create_task(self._worker()) for _ in range(self._config.concurrency)]

    async def _worker(self) -> None:
        while True:
            url = await self._frontier.get()
            result = await self._fetch_stage.fetch(url)
            await self._results.put(result)

    async def _stop_workers(self, workers: list[asyncio.Task[None]]) -> None:
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
