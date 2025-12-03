from typing import AsyncGenerator, Set

import aiohttp

from site_crawler.fetcher import Fetcher


class Crawler:
    def __init__(self, base_url: str, concurrency: int = 10, timeout: int = 10, max_pages: int = 100, fetcher = Fetcher()) -> None:
        self._base_url = base_url
        self._fetcher = fetcher

    async def crawl(self) -> AsyncGenerator[Set[str], None]:
        async with aiohttp.ClientSession() as session:
            await self._fetcher.fetch(session, url=self._base_url)

        yield {self._base_url}