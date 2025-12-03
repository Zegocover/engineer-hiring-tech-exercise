import asyncio
import logging
from typing import AsyncGenerator, Set
from urllib.parse import urlparse

import aiohttp

from site_crawler.extractor import get_urls_from_html
from site_crawler.fetcher import Fetcher


class Crawler:
    def __init__(self, fetcher = Fetcher()) -> None:
        self._fetcher = fetcher


    async def crawl(self, base_url: str) -> AsyncGenerator[Set[str], None]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        seen_urls: Set[str] = {base_url}

        await queue.put(base_url)
        async with aiohttp.ClientSession() as session:
            while not queue.empty():
                url = await queue.get()
                content = await self._fetcher.fetch(session, url)
                if content is None:
                    continue
                urls = get_urls_from_html(content, base_url)
                unique_urls = [url for url in urls if url not in seen_urls]
                valid_urls = [url for url in unique_urls if self.is_valid(url, base_url)]
                for url in valid_urls:
                    await queue.put(url)
                seen_urls.update(valid_urls)


        yield seen_urls

    def is_valid(self, url: str, base_url: str) -> bool:
        """Return True if `url` belongs to the same exact hostname as `base_url`.

        Subdomains are not allowed (e.g. `sub.example.com` != `example.com`).
        Treats different TLDs as different (e.g. `example.com` != `example.co.uk`).
        Comparison is case-insensitive.
        """
        try:
            p = urlparse(url)
            b = urlparse(base_url)
            if not p.hostname or not b.hostname:
                return False
            return p.hostname.lower() == b.hostname.lower()
        except Exception:
            logging.exception("Error validating URL")
            return False