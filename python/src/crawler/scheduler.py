"""Queue management and crawl scheduling logic."""

import asyncio
import logging
import time
from collections.abc import Iterable

from crawler import urls
from crawler.models import CrawlItem
from crawler.robots import RobotsPolicy


class Scheduler:
    """Holds crawl queues and the visited set."""

    def __init__(self, max_pages_crawled: int | None = None) -> None:
        self._candidates: asyncio.Queue[CrawlItem] = asyncio.Queue()
        self._crawl_queue: asyncio.PriorityQueue[
            tuple[float, int, CrawlItem]
        ] = asyncio.PriorityQueue()
        self._visited: set[str] = set()
        self._seq: int = 0
        self._in_flight: int = 0
        self._pages_crawled: int = 0
        self._max_pages_crawled: int | None = max_pages_crawled
        self._started = asyncio.Event()
        self._stop_scheduling = asyncio.Event()
        self._stop_event = asyncio.Event()

    @property
    def stop_event(self) -> asyncio.Event:
        return self._stop_event

    def stop(self) -> None:
        self._stop_event.set()

    async def enqueue_candidate(
        self,
        candidate: CrawlItem,
        robots_policy: RobotsPolicy | None = None,
    ) -> None:
        """Add a raw URL to the candidates queue."""
        if self._stop_scheduling.is_set():
            return
        if robots_policy and not robots_policy.is_allowed(candidate.url):
            logging.debug(
                "Skipping candidate due to robots.txt: %s", candidate.url
            )
            return
        await self._candidates.put(candidate)

    async def enqueue_candidate_urls(
        self,
        urls: Iterable[str],
        depth: int,
        robots_policy: RobotsPolicy | None = None,
    ) -> None:
        """Add multiple raw URLs to the candidates queue."""
        for url in urls:
            await self.enqueue_candidate(
                CrawlItem(url=url, depth=depth),
                robots_policy=robots_policy,
            )

    def _is_candidate_valid(self, url: str, base_url: str) -> bool:
        """Return True if the candidate URL is supported and in scope."""
        try:
            if not urls.is_supported_scheme(url):
                logging.debug(
                    "Found a URL with unsupported scheme (%s)... skipping.",
                    url,
                )
                return False
            if not urls.is_domain_in_scope(url, base_url):
                logging.debug(
                    "Found a URL that is not in scope (%s)... skipping.",
                    url,
                )
                return False
            return True
        except urls.UrlParsingError as exc:
            logging.debug(
                "Skipping candidate due to URL parsing issue: "
                "url=%s error=%s",
                url,
                exc,
            )
            return False

    async def run(
        self,
        base_url: str,
        max_depth: int,
        robots_policy: RobotsPolicy | None = None,
    ) -> None:
        # Queue the base URL
        self._visited.add(urls.normalise_for_dedupe(base_url))
        await self.enqueue_crawl_task(
            CrawlItem(url=base_url, depth=0),
            robots_policy=robots_policy,
        )
        self._started.set()

        # TODO: ensure worker resolves links before enqueueing candidates.
        # Run the scheduler loop
        while True:
            candidate = await self._wait_for_candidate_or_stop()
            if candidate is None:
                break
            try:
                if not self._stop_scheduling.is_set():
                    await self.process_candidate(
                        candidate,
                        base_url,
                        max_depth,
                        robots_policy=robots_policy,
                    )
            except Exception:
                logging.exception(
                    "Unexpected error while scheduling candidate: " "url=%s",
                    candidate.url,
                )
            finally:
                self._candidates.task_done()

    async def next_crawl_task(self) -> CrawlItem | None:
        """Return the next crawl task when it is due."""
        while True:
            result = await self._wait_for_crawl_task_or_stop()
            if result is None:
                return None
            available_at, seq, item = result
            now = time.monotonic()
            if available_at <= now:
                self._in_flight += 1
                return item
            await self._crawl_queue.put((available_at, seq, item))
            self._crawl_queue.task_done()
            await asyncio.sleep(min(available_at - now, 0.1))

    def crawl_task_done(self) -> None:
        """Mark the current crawl task as done."""
        self._in_flight = max(self._in_flight - 1, 0)
        self._crawl_queue.task_done()

    async def enqueue_crawl_task(
        self,
        item: CrawlItem,
        delay_s: float = 0.0,
        robots_policy: RobotsPolicy | None = None,
    ) -> None:
        """Enqueue a crawl task, optionally delayed by delay_s seconds."""
        if self._stop_event.is_set():
            return
        if robots_policy and not robots_policy.is_allowed(item.url):
            logging.debug(
                "Skipping crawl task due to robots.txt: %s", item.url
            )
            return
        available_at = time.monotonic() + max(delay_s, 0.0)
        self._seq += 1
        await self._crawl_queue.put((available_at, self._seq, item))

    async def process_candidate(
        self,
        candidate: CrawlItem,
        base_url: str,
        max_depth: int,
        robots_policy: RobotsPolicy | None = None,
    ) -> None:
        """Validate, dedupe, and enqueue a single candidate."""
        new_depth = candidate.depth + 1
        if new_depth > max_depth:
            logging.debug(
                "Skipping candidate beyond max_depth (%s > %s): %s",
                new_depth,
                max_depth,
                candidate.url,
            )
            return

        if not self._is_candidate_valid(candidate.url, base_url):
            return

        normalised_url = urls.normalise_for_dedupe(candidate.url)
        if normalised_url in self._visited:
            logging.debug(
                "Found a URL that we've visited (%s)... skipping.",
                candidate.url,
            )
            return

        self._visited.add(normalised_url)
        await self.enqueue_crawl_task(
            CrawlItem(url=candidate.url, depth=new_depth),
            robots_policy=robots_policy,
        )
        logging.debug(
            "Enqueued crawl task: url=%s depth=%s",
            candidate.url,
            new_depth,
        )

    def increment_pages_crawled(self) -> None:
        """Track crawled pages and stop if max_pages_crawled reached."""
        self._pages_crawled += 1
        if (
            self._max_pages_crawled is not None
            and self._pages_crawled >= self._max_pages_crawled
        ):
            logging.info(
                "Reached max_pages_crawled=%s, stopping crawl.",
                self._max_pages_crawled,
            )
            self._stop_scheduling.set()

    async def wait_for_shutdown(self) -> None:
        """Wait until it is safe to stop workers and scheduler."""
        await self._started.wait()
        while not self._stop_event.is_set():
            if self._stop_scheduling.is_set():
                await asyncio.gather(
                    self._candidates.join(),
                    self._crawl_queue.join(),
                )
                self._stop_event.set()
                return

            await asyncio.gather(
                self._candidates.join(),
                self._crawl_queue.join(),
            )
            if self._candidates.empty() and self._crawl_queue.empty():
                logging.info("No remaining tasks; stopping crawl.")
                self._stop_event.set()
                return
            await asyncio.sleep(0.05)

    async def _wait_for_candidate_or_stop(self) -> CrawlItem | None:
        """Wait for a candidate unless the stop event fires first."""
        return await self._wait_for_queue_or_stop(self._candidates.get)

    async def _wait_for_crawl_task_or_stop(
        self,
    ) -> tuple[float, int, CrawlItem] | None:
        """Wait for a crawl task unless the stop event fires first."""
        return await self._wait_for_queue_or_stop(self._crawl_queue.get)

    async def _wait_for_queue_or_stop(self, get_coro_factory):
        """Wait for a queue item unless the stop event fires first."""
        if self._stop_event.is_set():
            return None
        item_task = asyncio.create_task(get_coro_factory())
        stop_task = asyncio.create_task(self._stop_event.wait())
        # Wait for either a queue item or a stop signal so we do not
        # block forever on the queue when shutting down.
        done, _ = await asyncio.wait(
            {item_task, stop_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if stop_task in done:
            # Stop wins: cancel the pending queue get to avoid leaks.
            item_task.cancel()
            await asyncio.gather(item_task, return_exceptions=True)
            return None
        stop_task.cancel()
        await asyncio.gather(stop_task, return_exceptions=True)
        return item_task.result()
