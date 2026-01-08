"""Core crawler orchestration."""

import asyncio
from collections.abc import Callable

import httpx

from crawler.fetcher import FetchResult, fetch
from crawler.parser import extract_links
from crawler.url_utils import get_base_domain, process_url


class Crawler:
    """Async web crawler that crawls a single domain."""

    def __init__(
        self,
        start_url: str,
        max_concurrency: int = 10,
        timeout: float = 30.0,
        on_page_crawled: Callable[[str, list[str]], None] | None = None,
    ) -> None:
        """Initialise the crawler.

        Args:
            start_url: The URL to start crawling from.
            max_concurrency: Maximum number of concurrent requests.
            timeout: Request timeout in seconds.
            on_page_crawled: Callback called with (url, found_urls) for each page.
        """
        self.start_url = start_url
        self.base_domain = get_base_domain(start_url)
        self.max_concurrency = max_concurrency
        self.timeout = timeout
        self.on_page_crawled = on_page_crawled

        self.visited: set[str] = set()
        self.queue: asyncio.Queue[str] = asyncio.Queue()

    async def crawl(self) -> dict[str, list[str]]:
        """Crawl the site starting from start_url.

        Returns:
            Dict mapping each crawled URL to the list of URLs found on that page.
        """
        results: dict[str, list[str]] = {}
        semaphore = asyncio.Semaphore(self.max_concurrency)

        # Normalise and queue the start URL
        normalised_start = process_url(self.start_url, self.start_url, self.base_domain)
        if normalised_start is None:
            return results

        await self.queue.put(normalised_start)
        self.visited.add(normalised_start)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            workers = [
                asyncio.create_task(self._worker(client, semaphore, results))
                for _ in range(self.max_concurrency)
            ]

            await self.queue.join()

            for worker in workers:
                worker.cancel()

        return results

    async def _worker(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        results: dict[str, list[str]],
    ) -> None:
        """Worker that processes URLs from the queue."""
        while True:
            url = await self.queue.get()
            try:
                async with semaphore:
                    await self._process_url(client, url, results)
            finally:
                self.queue.task_done()

    async def _process_url(
        self,
        client: httpx.AsyncClient,
        url: str,
        results: dict[str, list[str]],
    ) -> None:
        """Fetch a URL, extract links, and queue new URLs."""
        result: FetchResult = await fetch(client, url)

        if result.error is not None or result.html is None:
            results[url] = []
            if self.on_page_crawled:
                self.on_page_crawled(url, [])
            return

        hrefs = extract_links(result.html)
        found_urls: list[str] = []

        for href in hrefs:
            normalised = process_url(href, url, self.base_domain)
            if normalised is not None:
                found_urls.append(normalised)
                if normalised not in self.visited:
                    self.visited.add(normalised)
                    await self.queue.put(normalised)

        results[url] = found_urls
        if self.on_page_crawled:
            self.on_page_crawled(url, found_urls)
