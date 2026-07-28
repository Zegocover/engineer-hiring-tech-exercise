import asyncio
import logging
import random
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)

from crawler.config import (
    DEFAULT_BACKOFF_BASE,
    DEFAULT_BACKOFF_MAX,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_MAX_RETRIES,
    RETRYABLE_STATUS_CODES,
)
from crawler.robots_cache import RobotsCache
from crawler.search import BredthFirstSearch


@dataclass
class CrawlResult:
    completed: bool
    visited: set[str]
    found_urls_by_domain: dict[str, set[str]] = field(default_factory=dict)

    @property
    def urls(self) -> set[str]:
        return self.visited


class LinkExtractor(HTMLParser):
    """Collects `href` attributes from `<a>` tags. Links inside HTML
    comments are skipped automatically, since HTMLParser never emits
    start-tag events for markup within a comment."""

    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value:
                self.hrefs.append(value)


class RetryPolicy:
    """Computes backoff delays for retryable responses (429/5xx)."""

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
        backoff_max: float = DEFAULT_BACKOFF_MAX,
    ) -> None:
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max

    def is_retryable(self, response: httpx.Response) -> bool:
        return response.status_code in RETRYABLE_STATUS_CODES

    def delay_for(self, response: httpx.Response, attempt: int) -> float:
        """attempt is 0-indexed (0 = first retry)."""
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return float(retry_after)
            except ValueError:
                pass
        backoff = min(self.backoff_base * (2**attempt), self.backoff_max)
        return backoff + random.uniform(0, backoff * 0.1)


class Crawler:
    def __init__(self, retry_policy: RetryPolicy | None = None) -> None:
        self.retry_policy = retry_policy or RetryPolicy()

    async def crawl(
        self,
        client: httpx.AsyncClient,
        start_url: str,
        timeout: float,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    ) -> CrawlResult:
        """Handles core crawling logic for the crawler."""
        self._client = client

        self._robots_cache = RobotsCache(client=client)
        robots_txt = await self._robots_cache.fetch_robots_txt(url=start_url)

        # A None result means robots.txt was unreachable in a way that denies
        # access (5xx, 401/403, redirect loop). Fail closed: an empty ruleset
        # would parse as "allow everything", inverting the intent.
        self._robots_blocked = robots_txt is None
        self._robot_rules = RobotFileParser()
        self._robot_rules.parse((robots_txt or "").splitlines())

        delay = self._robot_rules.crawl_delay(self._robots_cache.user_agent)
        self._crawl_delay = float(delay) if delay is not None else 0.0

        if self._robots_blocked:
            logger.warning(
                "Refusing to crawl %s: robots.txt could not be retrieved.", start_url
            )
            return CrawlResult(completed=True, visited=set(), found_urls_by_domain={})

        bfs = BredthFirstSearch(start_url, self._get_links, max_concurrency)
        try:
            visited, found_urls = await asyncio.wait_for(bfs.run(), timeout=timeout)
            return CrawlResult(
                completed=True, visited=visited, found_urls_by_domain=found_urls
            )
        except TimeoutError:
            return CrawlResult(
                completed=False,
                visited=bfs.visited,
                found_urls_by_domain=bfs.found_urls_by_domain,
            )

    async def _get_links(self, url: str) -> list[str]:
        """makes the request to the url and extracts the links to the caller."""
        if self._robots_blocked or not self._robot_rules.can_fetch(
            self._robots_cache.user_agent, url
        ):
            logger.info("Skipping %s (disallowed by robots.txt)", url)
            return []
        if self._crawl_delay:
            await asyncio.sleep(self._crawl_delay)
        logger.info("Fetching %s", url)
        response = await self._fetch(url)
        if response is None:
            logger.warning("Failed to fetch %s", url)
            return []
        content_type = response.headers.get("content-type")
        if content_type is not None and "text/html" not in content_type.lower():
            return []
        links = self._extract_links(response.text, base_url=url)
        logger.info("Found %d link(s) on %s", len(links), url)
        return links

    async def _fetch(self, url: str) -> httpx.Response | None:
        """Fetches a url, retrying on 429/5xx with backoff. Returns None if
        the page never succeeds within max_retries (caller treats it as a
        dead end rather than aborting the whole crawl)."""
        policy = self.retry_policy
        for attempt in range(policy.max_retries):
            try:
                response = await self._client.get(url)
            except httpx.HTTPError:
                return None
            if not policy.is_retryable(response):
                return response
            await asyncio.sleep(policy.delay_for(response, attempt))
        return None

    def _extract_links(self, text: str, base_url: str) -> list[str]:
        """
        Called with a dump of text and a url to parse and process.

        Returns all http(s) links found on the page, including
        off-origin ones, so callers can report them. Restricting
        traversal to the origin domain is the caller's responsibility.
        """
        parser = LinkExtractor()
        parser.feed(text)

        links: list[str] = []
        for href in parser.hrefs:
            resolved = urljoin(base_url, href)
            resolved, _fragment = urldefrag(resolved)
            parsed = urlsplit(resolved)
            if parsed.scheme not in ("http", "https"):
                continue
            links.append(resolved)
        return links
