from __future__ import annotations

import asyncio
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from .extractor import ContentExtractor
from .fetcher import Fetcher
from .filters import DomainFilter
from .frontier import Frontier
from .normaliser import URLNormaliser
from .robots import RobotsPolicy


@dataclass
class CrawlStats:
    pages_crawled: int = 0
    errors: int = 0
    robots_disallowed: int = 0

class Crawler:
    """The craler is a simple orchestration layer, it doesn't perform any requests, parsing,
    filtering, etc"""

    def __init__(
        self,
        base_url: str,
        *,
        fetcher: Fetcher,
        frontier: Frontier,
        normaliser: URLNormaliser,
        content_extractor: ContentExtractor,
        domain_filter: DomainFilter,
        robots_policy: RobotsPolicy,
        concurrency: int = 10,
    ) -> None:
        self._base_url = base_url
        self._fetcher = fetcher
        self._frontier = frontier
        self._domain_filter = domain_filter
        self._robots_policy = robots_policy
        self._concurrency = concurrency
        self._stats = CrawlStats()
        self._content_extractor = content_extractor
        self._normaliser = normaliser

    async def run(self) -> CrawlStats:
        seed = self._normaliser.normalise_url(self._base_url, self._base_url) or self._base_url
        self._frontier.add(seed)

        workers = [asyncio.create_task(self._worker()) for _ in range(self._concurrency)]
        await self._frontier.join()
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

        return self._stats

    async def _worker(self) -> None:
        while True:
            url = await self._frontier.next()
            try:
                await self._process(url)
            finally:
                self._frontier.task_done()

    async def _process(self, url: str) -> None:
        # First of all check if we are allowed to visit the url
        if not self._robots_policy.is_allowed(url):
            self._stats.robots_disallowed += 1
            self._frontier.mark_visited(url)
            return
        
        result = await self._fetcher.fetch(url)
        self._frontier.mark_visited(result.url)

        if result.html is None:
            self._stats.errors += 1
            return

        links = self._content_extractor.extract_content(result.html, result.url)
        self._write_output(result.url, links)
        self._stats.pages_crawled += 1

        for link in links:
            if self._domain_filter.is_allowed(link):
                self._frontier.add(link)

    @staticmethod
    def _write_output(page_url: str, links: Sequence[str]) -> None:
        # Builds the whole block into one string and issues a single write() call
        # (no `await` in between) so the other concurrent workers' output can't interleave.
        lines = [page_url, *(f"  {link}" for link in links), ""]
        sys.stdout.write("\n".join(lines) + "\n")