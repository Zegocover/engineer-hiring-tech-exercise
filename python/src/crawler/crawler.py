"""Async web crawler with BFS traversal."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field

import aiohttp

from .parser import extract_links, is_html_content_type
from .url_utils import extract_domain, is_same_domain, normalize_url, should_skip_url

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Result of crawling a single page."""

    url: str
    links: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class CrawlerConfig:
    """Configuration for the crawler."""

    concurrency: int = 10
    timeout: int = 30
    max_pages: int | None = None
    user_agent: str = "WebCrawler/1.0"


class Crawler:
    """Async web crawler using BFS traversal.

    Uses aiohttp for concurrent HTTP requests and BeautifulSoup
    for HTML parsing. Respects concurrency limits via semaphore.

    Example:
        >>> async def main():
        ...     crawler = Crawler("https://example.com")
        ...     async for result in crawler.crawl():
        ...         print(f"Page: {result.url}")
        ...         for link in result.links:
        ...             print(f"  -> {link}")
    """

    def __init__(
        self,
        base_url: str,
        config: CrawlerConfig | None = None,
        on_page_crawled: Callable[[CrawlResult], None] | None = None,
    ) -> None:
        """Initialize the crawler.

        Args:
            base_url: The starting URL to crawl.
            config: Crawler configuration options.
            on_page_crawled: Optional callback for each crawled page.
        """
        self.base_url = normalize_url(base_url)
        self.base_domain = extract_domain(self.base_url)
        self.config = config or CrawlerConfig()
        self.on_page_crawled = on_page_crawled

        self._visited: set[str] = set()
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._semaphore: asyncio.Semaphore | None = None
        self._pages_crawled = 0

    async def crawl(self) -> list[CrawlResult]:
        """Crawl the website starting from base_url.

        Uses BFS traversal with concurrent workers bounded by semaphore.

        Returns:
            List of CrawlResult objects for all crawled pages.
        """
        self._semaphore = asyncio.Semaphore(self.config.concurrency)
        results: list[CrawlResult] = []

        # Configure connection pooling
        connector = aiohttp.TCPConnector(
            limit=self.config.concurrency * 2,
            limit_per_host=self.config.concurrency,
            ttl_dns_cache=300,
        )

        timeout = aiohttp.ClientTimeout(total=self.config.timeout)

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": self.config.user_agent},
        ) as session:
            # Seed the queue with the base URL
            await self._queue.put(self.base_url)
            self._visited.add(self.base_url)

            # Process queue until empty
            while not self._queue.empty() or self._has_pending_tasks():
                # Check max pages limit
                if self.config.max_pages and self._pages_crawled >= self.config.max_pages:
                    logger.info(f"Reached max pages limit: {self.config.max_pages}")
                    break

                try:
                    url = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                result = await self._fetch_page(session, url)
                results.append(result)
                self._pages_crawled += 1

                if self.on_page_crawled:
                    self.on_page_crawled(result)

                # Add new URLs to queue
                for link in result.links:
                    if self._should_enqueue(link):
                        self._visited.add(link)
                        await self._queue.put(link)

                self._queue.task_done()

        return results

    def _has_pending_tasks(self) -> bool:
        """Check if there are tasks still being processed."""
        # In this simple implementation, we process synchronously
        # so there are no pending tasks beyond the queue
        return False

    def _should_enqueue(self, url: str) -> bool:
        """Determine if a URL should be added to the crawl queue.

        Args:
            url: The URL to check.

        Returns:
            True if the URL should be crawled.
        """
        # Already visited
        if url in self._visited:
            return False

        # Not same domain
        if not is_same_domain(url, self.base_domain):
            return False

        # Should skip (mailto, etc.)
        if should_skip_url(url):
            return False

        return True

    async def _fetch_page(self, session: aiohttp.ClientSession, url: str) -> CrawlResult:
        """Fetch and parse a single page.

        Args:
            session: The aiohttp session to use.
            url: The URL to fetch.

        Returns:
            CrawlResult with the URL, discovered links, and any error.
        """
        async with self._semaphore:  # type: ignore[union-attr]
            try:
                async with session.get(url, allow_redirects=True) as response:
                    # Check if response is HTML
                    content_type = response.headers.get("Content-Type", "")
                    if not is_html_content_type(content_type):
                        logger.debug(f"Skipping non-HTML: {url} ({content_type})")
                        return CrawlResult(url=url, links=[])

                    # Check status code
                    if response.status >= 400:
                        error_msg = f"HTTP {response.status}"
                        logger.warning(f"Error fetching {url}: {error_msg}")
                        return CrawlResult(url=url, error=error_msg)

                    # Parse HTML and extract links
                    html = await response.text()

                    # Use final URL after redirects for resolving relative links
                    final_url = str(response.url)
                    links = extract_links(html, final_url)

                    # Filter to same domain only
                    same_domain_links = [
                        link for link in links if is_same_domain(link, self.base_domain)
                    ]

                    return CrawlResult(url=url, links=same_domain_links)

            except asyncio.TimeoutError:
                error_msg = "Request timed out"
                logger.warning(f"Timeout fetching {url}")
                return CrawlResult(url=url, error=error_msg)

            except aiohttp.ClientError as e:
                error_msg = str(e)
                logger.warning(f"Error fetching {url}: {error_msg}")
                return CrawlResult(url=url, error=error_msg)

            except Exception as e:
                error_msg = f"Unexpected error: {e}"
                logger.error(f"Unexpected error fetching {url}: {e}")
                return CrawlResult(url=url, error=error_msg)
