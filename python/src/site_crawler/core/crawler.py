"""The crawler: frontier, workers, the single writer task and stats.

Concurrency model: N identical workers each fetch -> parse -> enqueue, and
hand page results to one writer task, so writers see results one at a time
and in a stable order. The frontier is a queue plus a seen-set; a URL is
marked seen when it is *enqueued*, which (on a single-threaded event loop,
with no ``await`` between check and insert) guarantees each URL is fetched
at most once.

robots.txt is read per host. The first URL seen for a host waits in that
host's pending list while a ``_LoadRobots`` item on the same queue fetches
the host's robots.txt; the waiting URLs are then admitted. Because loading is
ordinary queue work, the crawl can't finish while a load is outstanding.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from urllib.parse import urlsplit

from site_crawler.core.robots import RobotsGate
from site_crawler.core.urls import HostScope, host_and_port, normalise, resolve_and_normalise
from site_crawler.fetchers import DefaultHttpxFetcher
from site_crawler.interfaces import Fetcher, Parser, Writer
from site_crawler.models import CrawlConfig, CrawlStats, FetchError, FetchResult, PageResult
from site_crawler.parsers import DefaultSelectolaxParser
from site_crawler.writers import TextWriter

logger = logging.getLogger(__name__)

Host = tuple[str, int | None]  # hostname, non-default port


@dataclass(frozen=True, slots=True)
class _Fetch:
    url: str
    depth: int


@dataclass(frozen=True, slots=True)
class _LoadRobots:
    host: Host
    origin: str  # scheme://host[:port]/


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc.rpartition('@')[2]}/"


class Crawler:
    def __init__(
        self,
        config: CrawlConfig,
        *,
        fetcher: Fetcher | None = None,
        parser: Parser | None = None,
        writer: Writer | None = None,
    ) -> None:
        """Create a crawl. Components left as ``None`` use the package defaults:
        :class:`DefaultHttpxFetcher`, :class:`DefaultSelectolaxParser` and :class:`TextWriter`.
        """
        self._config = config
        self._fetcher = fetcher or DefaultHttpxFetcher(
            timeout=config.timeout,
            max_connections=config.concurrency,
            user_agent=config.user_agent,
        )
        self._parser = parser or DefaultSelectolaxParser()
        self._writer = writer or TextWriter()

        seed = normalise(config.base_url)
        if seed is None:  # CrawlConfig already validates this
            raise ValueError(f"unusable base URL {config.base_url!r}")
        self._seed = seed
        self._scope = HostScope(seed, config.host_patterns)

        self._queue: asyncio.Queue[_Fetch | _LoadRobots] = asyncio.Queue()
        self._results: asyncio.Queue[PageResult | None] = asyncio.Queue(
            maxsize=config.concurrency * 2
        )
        self._seen: set[str] = set()
        self._enqueued = 0
        self._robots: dict[Host, RobotsGate] = {}
        self._pending: dict[Host, list[tuple[str, int]]] = {}  # waiting for robots.txt
        self._host_slots: dict[Host, asyncio.Semaphore] = {}  # per_host_concurrency
        self.stats = CrawlStats()

    async def run(self) -> CrawlStats:
        """Crawl until no work remains and return the summary.

        :class:`FetchError` is recorded and the crawl continues. Any other
        exception from a component stops the crawl and is re-raised after
        the writer and fetcher are closed.
        """
        tasks: list[asyncio.Task[None]] = []
        try:
            # The seed is always fetched: the user asked for it explicitly. With
            # robots.txt on, it waits for its host's robots.txt like any other URL.
            self._enqueue(self._seed, 0)
            writer_task = asyncio.create_task(self._write_loop(), name="writer")
            workers = [
                asyncio.create_task(self._worker(), name=f"worker-{i}")
                for i in range(self._config.concurrency)
            ]
            join_task = asyncio.create_task(self._queue.join(), name="join")
            tasks = [writer_task, join_task, *workers]

            # Workers and the writer loop forever, so if any of them finishes
            # before the queue drains it has failed.
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            self._raise_if_failed([writer_task, *workers])

            await self._results.put(None)
            await writer_task
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            try:
                await self._writer.aclose()
            finally:
                await self._fetcher.aclose()
        return self.stats

    @staticmethod
    def _raise_if_failed(tasks: list[asyncio.Task[None]]) -> None:
        for task in tasks:
            if task.done() and not task.cancelled() and (exc := task.exception()):
                raise exc

    def _enqueue(self, url: str, depth: int) -> None:
        # No awaits in here: check-and-insert must be atomic on the event loop.
        if url in self._seen or not self._scope.allows(url):
            return
        if self._config.max_depth is not None and depth > self._config.max_depth:
            return
        if self._budget_spent():
            return
        self._seen.add(url)
        host = host_and_port(url)
        if not self._config.respect_robots or host is None or host in self._robots:
            self._admit(url, depth)
        elif host in self._pending:
            self._pending[host].append((url, depth))
        else:
            self._pending[host] = [(url, depth)]
            self._queue.put_nowait(_LoadRobots(host, _origin(url)))

    def _admit(self, url: str, depth: int) -> None:
        """Queue a fetch of a seen, in-scope URL once its host's robots.txt is known."""
        if self._budget_spent():
            return
        gate = self._robots.get(host_and_port(url) or ("", None))
        if gate is not None and url != self._seed and not gate.allowed(url):
            self.stats.robots_skipped += 1  # counted once: the URL is already seen
            return
        self._enqueued += 1
        self._queue.put_nowait(_Fetch(url, depth))

    def _budget_spent(self) -> bool:
        return self._config.max_pages is not None and self._enqueued >= self._config.max_pages

    async def _worker(self) -> None:
        while True:
            item = await self._queue.get()
            try:
                if isinstance(item, _LoadRobots):
                    await self._load_robots(item)
                else:
                    await self._process(item.url, item.depth)
            finally:
                self._queue.task_done()

    def _host_slot(self, host: Host | None) -> contextlib.AbstractAsyncContextManager[object]:
        """Limit requests in flight to ``host`` when ``per_host_concurrency`` is set."""
        limit = self._config.per_host_concurrency
        if limit is None or host is None:
            return contextlib.nullcontext()
        return self._host_slots.setdefault(host, asyncio.Semaphore(limit))

    async def _load_robots(self, item: _LoadRobots) -> None:
        async with self._host_slot(item.host):
            self._robots[item.host] = await RobotsGate.load(
                self._fetcher, item.origin, self._config.user_agent
            )
        for url, depth in self._pending.pop(item.host):
            self._admit(url, depth)

    async def _process(self, url: str, depth: int) -> None:
        try:
            async with self._host_slot(host_and_port(url)):
                page = await self._fetcher.fetch(url)
        except FetchError as exc:
            self.stats.errors += 1
            self.stats.error_urls.append(url)
            logger.warning("fetch failed: %s", exc)
            return

        self.stats.fetched += 1
        if url == self._seed:
            self.stats.seed_ok = True

        page_url = self._accept_final_url(url, page)
        if page_url is None or not page.is_html:
            return

        links = self._extract_links(page)
        await self._results.put(PageResult(page_url, links))

        for link in links:
            self._enqueue(link, depth + 1)

    def _accept_final_url(self, url: str, page: FetchResult) -> str | None:
        """Return the URL to report for ``page``, or ``None`` to drop it."""
        final = normalise(page.final_url) or url
        if final == url:
            return url
        if not self._scope.allows(final):
            logger.info("redirect left the crawl scope: %s -> %s", url, final)
            return None
        if final in self._seen:
            # Target is already queued or crawled under its own URL.
            return None
        self._seen.add(final)
        return final

    def _extract_links(self, page: FetchResult) -> tuple[str, ...]:
        links: dict[str, None] = {}  # ordered set
        for href in self._parser.parse(page):
            link = resolve_and_normalise(page.final_url, href)
            if link is not None:
                links.setdefault(link)
        return tuple(links)

    async def _write_loop(self) -> None:
        while (result := await self._results.get()) is not None:
            await self._writer.write(result)
            self.stats.pages += 1
