"""Core async web crawler using a worker-pool pattern with bounded concurrency."""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import aiohttp

from crawler.parser import extract_links, get_domain, normalise_url

logger = logging.getLogger(__name__)

DEFAULT_MAX_CONCURRENCY = 10
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_USER_AGENT = "WebCrawler/1.0"


@dataclass
class PageResult:
    """Result of crawling a single page."""

    url: str
    links: set[str] = field(default_factory=set)
    internal_links: set[str] = field(default_factory=set)
    status_code: int | None = None
    error: str | None = None
    elapsed_ms: float = 0.0


@dataclass
class CrawlStats:
    """Aggregated statistics for a crawl session."""

    pages_crawled: int = 0
    pages_failed: int = 0
    total_links_found: int = 0
    elapsed_seconds: float = 0.0


class Crawler:
    """Async web crawler that discovers and reports links within a single domain.

    Architecture:
    - A shared asyncio.Queue holds URLs pending processing.
    - A pool of worker coroutines consume from the queue concurrently.
    - An asyncio.Semaphore bounds the number of simultaneous HTTP requests.
    - A set tracks visited URLs to prevent duplicates.
    - An optional callback is invoked for each page result (e.g. for output).

    This design allows high throughput while respecting resource limits. The
    workers are cooperative: each discovers new URLs and feeds them back into
    the queue, creating a BFS traversal of the site graph.
    """

    def __init__(
        self,
        base_url: str,
        *,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
        max_pages: int = 0,
        respect_robots: bool = False,
        on_page_crawled: Callable[[PageResult], None] | None = None,
    ):
        self.base_url = normalise_url(base_url)
        self.base_domain = get_domain(self.base_url)
        self.max_concurrency = max_concurrency
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.user_agent = user_agent
        self.max_pages = max_pages
        self.respect_robots = respect_robots
        self.on_page_crawled = on_page_crawled

        self._visited: set[str] = set()
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._results: list[PageResult] = []
        self._lock = asyncio.Lock()
        self._in_flight: int = 0
        self._pages_claimed: int = 0

    async def _fetch_page(
        self, session: aiohttp.ClientSession, url: str
    ) -> PageResult:
        """Fetch a page and extract links. Returns a PageResult regardless of outcome."""
        start = time.perf_counter()
        try:
            async with session.get(url, allow_redirects=True) as response:
                elapsed = (time.perf_counter() - start) * 1000

                # Only parse HTML responses
                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    logger.debug("Skipping non-HTML: %s (%s)", url, content_type)
                    return PageResult(
                        url=url,
                        status_code=response.status,
                        error=f"non-html ({content_type})",
                        elapsed_ms=elapsed,
                    )

                html = await response.text(errors="replace")
                internal_links, all_links = extract_links(html, url, self.base_domain)

                return PageResult(
                    url=url,
                    links=all_links,
                    internal_links=internal_links,
                    status_code=response.status,
                    elapsed_ms=elapsed,
                )

        except TimeoutError:
            elapsed = (time.perf_counter() - start) * 1000
            logger.warning("Timeout fetching %s", url)
            return PageResult(url=url, error="timeout", elapsed_ms=elapsed)
        except aiohttp.ClientError as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.warning("Client error fetching %s: %s", url, e)
            return PageResult(url=url, error=str(e), elapsed_ms=elapsed)
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("Unexpected error fetching %s: %s", url, e)
            return PageResult(url=url, error=f"unexpected: {e}", elapsed_ms=elapsed)

    def _limit_reached(self) -> bool:
        """Check if the max_pages limit has been reached."""
        return self.max_pages > 0 and self._pages_claimed >= self.max_pages

    async def _claim_slot(self) -> bool:
        """Try to claim a crawl slot. Returns True if allowed to proceed."""
        async with self._lock:
            if self.max_pages > 0 and self._pages_claimed >= self.max_pages:
                return False
            self._pages_claimed += 1
            return True

    async def _worker(self, session: aiohttp.ClientSession) -> None:
        """Worker loop: consume URLs from the queue, fetch, enqueue discoveries."""
        while True:
            try:
                url = await asyncio.wait_for(self._queue.get(), timeout=2.0)
            except TimeoutError:
                # No work and nothing in-flight means we're done
                if self._queue.empty() and self._in_flight == 0:
                    return
                continue

            # Try to claim a slot; if limit reached, skip
            if not await self._claim_slot():
                self._queue.task_done()
                continue

            async with self._lock:
                self._in_flight += 1

            try:
                async with self._semaphore:
                    result = await self._fetch_page(session, url)

                self._results.append(result)

                # Notify callback
                if self.on_page_crawled:
                    self.on_page_crawled(result)

                # Enqueue newly discovered internal URLs (if limit not reached)
                if not self._limit_reached():
                    for link in result.internal_links:
                        async with self._lock:
                            if link not in self._visited:
                                self._visited.add(link)
                                await self._queue.put(link)
            finally:
                async with self._lock:
                    self._in_flight -= 1
                self._queue.task_done()

    async def crawl(self) -> list[PageResult]:
        """Execute the crawl starting from the base URL.

        Returns a list of PageResult objects for all pages visited.
        """
        start_time = time.perf_counter()

        self._visited.add(self.base_url)
        await self._queue.put(self.base_url)

        connector = aiohttp.TCPConnector(
            limit=self.max_concurrency,
            limit_per_host=self.max_concurrency,
            ttl_dns_cache=300,
            enable_cleanup_closed=True,
        )
        headers = {"User-Agent": self.user_agent}

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers=headers,
        ) as session:
            workers = [
                asyncio.create_task(self._worker(session))
                for _ in range(self.max_concurrency)
            ]

            # Wait until the queue is fully drained
            await self._queue.join()

            # Signal workers to stop and clean up
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

        elapsed = time.perf_counter() - start_time
        logger.info(
            "Crawl complete: %d pages in %.2fs", len(self._results), elapsed
        )

        return self._results

    def get_stats(self) -> CrawlStats:
        """Compute aggregate statistics from collected results."""
        failed = sum(1 for r in self._results if r.error)
        total_links = sum(len(r.links) for r in self._results)
        return CrawlStats(
            pages_crawled=len(self._results),
            pages_failed=failed,
            total_links_found=total_links,
        )
