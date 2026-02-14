from __future__ import annotations

import asyncio
import logging
from collections import deque

import aiohttp

from crawler.worker import Result, Worker, WorkItem


class Crawler:
    def __init__(
        self,
        base_url: str,
        *,
        batch_size: int = 10,
        max_urls: int | None = None,
        timeout: float = 10.0,
        retries: int = 1,
        output: str | None = None,
        quiet: bool = False,
    ) -> None:
        if batch_size < 1 or batch_size > 10:
            raise ValueError("batch_size must be between 1 and 10")
        if max_urls is not None and (max_urls < 1 or max_urls > 1000):
            raise ValueError("max_urls must be between 1 and 1000")
        if timeout < 0 or timeout > 10:
            raise ValueError("timeout must be between 0 and 10")
        if retries < 0 or retries > 3:
            raise ValueError("retries must be between 0 and 3")

        self._base_url = base_url
        self._batch_size = batch_size
        self._max_urls = max_urls
        self._timeout = timeout
        self._retries = retries
        self._output = output
        self._quiet = quiet

        self._results_by_url: dict[str, Result] = {}
        self._results: list[Result] = []
        self._visited: set[str] = set()
        self._scheduled: set[str] = set()
        self._queue: deque[WorkItem] = deque()
        self._seed()
        self._started = False
        self._logger = logging.getLogger(__name__)

    async def crawl(self) -> None:
        if self._started:
            raise RuntimeError("Crawler instances are single-use; create a new one.")
        self._started = True
        self._logger.info("Starting crawl for %s", self._base_url)

        timeout = aiohttp.ClientTimeout(total=self._timeout)
        headers = {"User-Agent": "ZegoCrawler/1.0"}
        connector = aiohttp.TCPConnector(limit=self._batch_size)

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
            connector=connector,
        ) as session:
            worker = Worker(base_url=self._base_url, session=session)

            try:
                while self._queue:
                    batch = self._dequeue_batch()
                    batch_results = await self._fetch_batch(worker, batch)
                    self._store_results(batch_results)
                    self._enqueue_discovered(batch_results)
                    self._handle_retries(batch_results)
                    self._logger.info(
                        "Batch fetched=%d queued=%d scheduled=%d visited=%d",
                        len(batch_results),
                        len(self._queue),
                        len(self._scheduled),
                        len(self._visited),
                    )
            except (KeyboardInterrupt, asyncio.CancelledError):
                self._logger.warning(
                    "Crawl interrupted; emitting partial results (%d pages)",
                    len(self._results),
                )
                self._emit_outputs()
                return

        self._logger.info("Crawl finished (%d pages)", len(self._results))
        self._emit_outputs()

    def _seed(self) -> None:
        self._scheduled.add(self._base_url)
        self._queue.append(WorkItem(self._base_url))

    def _dequeue_batch(self) -> list[WorkItem]:
        batch: list[WorkItem] = []
        while self._queue and len(batch) < self._batch_size:
            batch.append(self._queue.popleft())
        return batch

    async def _fetch_batch(
        self, worker: Worker, batch: list[WorkItem]
    ) -> list[tuple[WorkItem, Result]]:
        tasks = [worker.fetch(item.url) for item in batch]
        results = await asyncio.gather(*tasks)
        return list(zip(batch, results, strict=True))

    def _store_results(self, results: list[tuple[WorkItem, Result]]) -> None:
        for item, result in results:
            self._results_by_url[result.url] = result
            if result.error is None:
                self._results.append(result)
                self._visited.add(result.url)
            elif item.attempts >= self._retries:
                self._results.append(result)

    def _enqueue_discovered(self, results: list[tuple[WorkItem, Result]]) -> None:
        for _, result in results:
            for link in result.crawlable_links:
                if link in self._scheduled:
                    continue
                if (
                    self._max_urls is not None
                    and len(self._scheduled) >= self._max_urls
                ):
                    return
                self._scheduled.add(link)
                self._queue.append(WorkItem(link))

    def _handle_retries(self, results: list[tuple[WorkItem, Result]]) -> None:
        for item, result in results:
            if result.error is None:
                continue
            if item.attempts >= self._retries:
                continue
            self._queue.append(WorkItem(item.url, attempts=item.attempts + 1))

    def _emit_outputs(self) -> None:
        stdout_text = self._format_output(with_index=False)
        file_text = self._format_output(with_index=True)

        if not self._quiet and stdout_text:
            print(stdout_text)
        if self._output and file_text:
            with open(self._output, "w", encoding="utf-8") as handle:
                handle.write(file_text)
                handle.write("\n")

    def _format_output(self, *, with_index: bool) -> str:
        if not self._results:
            return ""
        lines: list[str] = []
        for index, result in enumerate(self._results, start=1):
            lines.append(result.to_text(page_index=index if with_index else None))
        return "\n\n".join(lines)
