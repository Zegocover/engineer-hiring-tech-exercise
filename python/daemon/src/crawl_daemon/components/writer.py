"""The daemon's writer: stores each job's pages and distinct links as the crawl runs."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable

from site_crawler.models import PageResult

from crawl_daemon.components.parser import ParseCache
from crawl_daemon.models import JobStats, utcnow
from crawl_daemon.storage import Storage

logger = logging.getLogger(__name__)


class StorageWriteError(Exception):
    """Results could not be stored; it stops the crawl and fails the job."""


class StorageWriter:
    """Buffers results and stores them in batches.

    A batch is written once it holds ``batch_size`` pages or ``flush_interval``
    seconds after its first page, whichever comes first, so results are
    readable shortly after the crawl reports them without one transaction
    per page. Each flush also saves the job's live statistics and the parse
    cache's new entries. ``aclose`` stores whatever is left, so every page is
    stored before the job's final status is.

    A failed page write is raised from the next ``write`` or ``aclose``,
    which stops the crawl. A failed parse cache write is only logged.
    """

    def __init__(
        self,
        storage: Storage,
        job_id: str,
        *,
        stats: Callable[[], JobStats],
        cache: ParseCache,
        batch_size: int = 50,
        flush_interval: float = 0.5,
    ) -> None:
        self._storage = storage
        self._job_id = job_id
        self._stats = stats
        self._cache = cache
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._pages: list[tuple[int, PageResult]] = []
        self._links: list[tuple[int, str]] = []
        self._seen: set[str] = set()
        self._next_page = 0
        self._lock = asyncio.Lock()
        self._timer: asyncio.Task[None] | None = None
        self._error: BaseException | None = None
        self._closed = False

    async def write(self, result: PageResult) -> None:
        self._raise_if_failed()
        self._pages.append((self._next_page, result))
        self._next_page += 1
        for link in result.links:
            if link not in self._seen:
                self._seen.add(link)
                self._links.append((len(self._seen) - 1, link))
        if len(self._pages) >= self._batch_size:
            self._cancel_timer()
            await self._flush()
        elif self._timer is None:
            self._timer = asyncio.create_task(self._flush_later(), name=f"flush-{self._job_id}")

    async def aclose(self) -> None:
        if not self._closed:
            self._closed = True
            self._cancel_timer()
            await self._flush()
        self._raise_if_failed()

    async def _flush_later(self) -> None:
        await asyncio.sleep(self._flush_interval)
        self._timer = None  # from here on, flushing: never cancelled (see _cancel_timer)
        # A failure is recorded in self._error and raised by the next write or aclose.
        with contextlib.suppress(StorageWriteError):
            await self._flush()

    def _cancel_timer(self) -> None:
        # The timer is only ever cancelled while it sleeps: it clears itself
        # before flushing, with no await in between.
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    async def _flush(self) -> None:
        async with self._lock:
            if self._error is not None:
                raise StorageWriteError(f"could not store results: {self._error}")
            pages, self._pages = self._pages, []
            links, self._links = self._links, []
            try:
                await self._storage.append_results(self._job_id, pages, links, self._stats())
            except Exception as exc:
                self._error = exc
                raise StorageWriteError(f"could not store results: {exc}") from exc
            entries = self._cache.drain()
            if entries:
                try:
                    await self._storage.put_parsed_links(entries, utcnow())
                except Exception:
                    logger.warning(
                        "could not store %d parse cache entries for job %s",
                        len(entries),
                        self._job_id,
                        exc_info=True,
                    )

    def _raise_if_failed(self) -> None:
        if self._error is not None:
            raise StorageWriteError(f"could not store results: {self._error}") from self._error
