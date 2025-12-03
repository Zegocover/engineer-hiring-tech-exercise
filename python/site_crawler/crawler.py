from typing import AsyncGenerator, Set

import aiohttp

from site_crawler.extractor import get_urls_from_html
from site_crawler.fetcher import Fetcher


class Crawler:
    def __init__(self, base_url: str, concurrency: int = 10, timeout: int = 10, max_pages: int = 100, fetcher = Fetcher()) -> None:
        self._base_url = base_url
        self._fetcher = fetcher
        self.seen_urls: Set[str] = set()

    async def crawl(self) -> AsyncGenerator[Set[str], None]:
        async with aiohttp.ClientSession() as session:
            content = await self._fetcher.fetch(session, url=self._base_url)

            urls = get_urls_from_html(content, self._base_url)
            unique_urls = [url for url in urls if url not in self.seen_urls]
            valid_urls = [url for url in unique_urls if self.is_valid(url)]

            print(valid_urls)

        yield {self._base_url}

    def is_valid(self, url: str) -> bool:
        # Placeholder for URL validation logic
        return True