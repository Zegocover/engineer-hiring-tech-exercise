from __future__ import annotations

import asyncio
from collections import deque

from crawler.page_worker import PageResult, PageWorker, WorkItem


class SiteCrawler:
    def __init__(
        self,
        base_url: str,
        *,
        batch_size: int = 10,
        max_urls: int | None = None,
        timeout: float = 10.0,
        retries: int = 1,
        output: str | None = None,
        output_format: str = "text",
    ) -> None:
        if batch_size < 1 or batch_size > 10:
            raise ValueError("batch_size must be between 1 and 10")
        if max_urls is not None and (max_urls < 1 or max_urls > 1000):
            raise ValueError("max_urls must be between 1 and 1000")
        if timeout < 0 or timeout > 10:
            raise ValueError("timeout must be between 0 and 10")
        if retries < 0 or retries > 3:
            raise ValueError("retries must be between 0 and 3")

        self.base_url = base_url
        self.batch_size = batch_size
        self.max_urls = max_urls
        self.timeout = timeout
        self.retries = retries
        self.output = output
        self.output_format = output_format

        self._results_by_url: dict[str, PageResult] = {}
        self._visited: set[str] = set()
        self._scheduled: set[str] = set()
        self._queue: deque[WorkItem] = deque()
        self._worker = PageWorker(
            base_url=self.base_url,
            timeout=self.timeout,
            retries=self.retries,
        )
        self._seed()
        self._started = False

    async def crawl(self) -> None:
        if self._started:
            raise RuntimeError(
                "SiteCrawler instances are single-use; create a new one."
            )
        self._started = True

        while self._queue:
            batch = self._dequeue_batch()
            results = await self._fetch_batch(batch)
            self._store_results(results)
            should_stop = self._enqueue_discovered(results)
            if should_stop:
                return

    def _seed(self) -> None:
        self._scheduled.add(self.base_url)
        self._queue.append(WorkItem(self.base_url))

    def _dequeue_batch(self) -> list[WorkItem]:
        batch: list[WorkItem] = []
        while self._queue and len(batch) < self.batch_size:
            batch.append(self._queue.popleft())
        return batch

    async def _fetch_batch(self, batch: list[WorkItem]) -> list[PageResult]:
        tasks = [self._worker.fetch(item.url) for item in batch]
        return await asyncio.gather(*tasks)

    def _store_results(self, results: list[PageResult]) -> None:
        for result in results:
            self._results_by_url[result.url] = result
            print(result.to_text())
            if result.error is None:
                self._visited.add(result.url)

    def _enqueue_discovered(self, results: list[PageResult]) -> bool:
        for result in results:
            for link in result.crawlable_links:
                if link in self._scheduled:
                    continue
                if self.max_urls is not None and len(self._scheduled) >= self.max_urls:
                    return True
                self._scheduled.add(link)
                self._queue.append(WorkItem(link))
        return False
