"""The crawl orchestrator: a bounded pool of async workers over a shared frontier."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from crawler.extractor import LinkExtractor
from crawler.fetcher import Fetcher
from crawler.models import PageResult
from crawler.url import get_host, normalize, same_site

DEFAULT_CONCURRENCY = 10


class Crawler:
    """Crawls a single site, emitting a :class:`PageResult` per page visited."""

    def __init__(
        self,
        fetcher: Fetcher,
        extractor: LinkExtractor,
        *,
        base_url: str,
        concurrency: int = DEFAULT_CONCURRENCY,
        max_pages: int | None = None,
        include_subdomains: bool = False,
    ) -> None:
        host = get_host(base_url)
        if host is None:
            raise ValueError(f"base_url must be an absolute http(s) URL with a host: {base_url!r}")
        if concurrency < 1:
            raise ValueError("concurrency must be >= 1")

        self._fetcher = fetcher
        self._extractor = extractor
        self._base_host = host
        self._concurrency = concurrency
        self._max_pages = max_pages
        self._include_subdomains = include_subdomains
        self._seed = normalize(base_url)

        # Per-crawl state; (re)initialised in crawl().
        self._frontier: asyncio.Queue[str] = asyncio.Queue()
        self._results: asyncio.Queue[PageResult | None] = asyncio.Queue()
        self._visited: set[str] = set()
        self._scheduled = 0

    async def crawl(self) -> AsyncIterator[PageResult]:
        """Yield a :class:`PageResult` for each page reachable from ``base_url``.

        Not safe to run concurrently on the same instance; run sequentially or
        create a new instance per crawl.
        """
        self._frontier = asyncio.Queue()
        self._results = asyncio.Queue()
        self._visited = set()
        self._scheduled = 0

        self._schedule(self._seed)

        # A fixed pool: its size is the cap on in-flight requests, so no separate
        # semaphore is needed, and one event-loop thread means shared state
        # (visited, scheduled) needs no locking.
        workers = [
            asyncio.create_task(self._worker(), name=f"crawl-worker-{i}")
            for i in range(self._concurrency)
        ]
        watcher = asyncio.create_task(self._signal_when_drained(), name="crawl-watcher")
        try:
            while True:
                page = await self._results.get()
                if page is None:
                    break
                yield page
        finally:
            for task in (*workers, watcher):
                task.cancel()
            await asyncio.gather(*workers, watcher, return_exceptions=True)

    async def _signal_when_drained(self) -> None:
        # join() returns once every scheduled URL has been task_done()'d; the
        # None sentinel then stops the crawl() consumer loop.
        await self._frontier.join()
        await self._results.put(None)

    async def _worker(self) -> None:
        while True:
            url = await self._frontier.get()
            try:
                page = await self._crawl_one(url)
                self._results.put_nowait(page)
            except Exception as exc:  # noqa: BLE001 - a worker must never die silently
                self._results.put_nowait(
                    PageResult(url=url, links=(), error=f"{type(exc).__name__}: {exc}")
                )
            finally:
                # Only after _crawl_one has enqueued this page's children, so
                # join() can't report the frontier drained prematurely.
                self._frontier.task_done()

    async def _crawl_one(self, url: str) -> PageResult:
        result = await self._fetcher.fetch(url)
        if result.error is not None:
            return PageResult(url=url, links=(), status_code=result.status_code, error=result.error)

        # Dedupe the post-redirect location so we don't fetch it again if it is
        # later discovered as a link in its own right.
        self._visited.add(normalize(result.final_url))

        links: tuple[str, ...] = ()
        if result.text is not None and self._is_in_scope(result.final_url):
            links = self._extractor.extract(result.final_url, result.text)
            for link in links:
                if self._is_in_scope(link):
                    self._schedule(link)

        return PageResult(url=url, links=links, status_code=result.status_code)

    def _schedule(self, url: str) -> None:
        canonical = normalize(url)
        if canonical in self._visited:
            return
        if self._max_pages is not None and self._scheduled >= self._max_pages:
            return
        self._visited.add(canonical)
        self._scheduled += 1
        self._frontier.put_nowait(canonical)

    def _is_in_scope(self, url: str) -> bool:
        return same_site(url, self._base_host, include_subdomains=self._include_subdomains)
