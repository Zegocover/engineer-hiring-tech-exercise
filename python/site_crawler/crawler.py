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


    async def crawl(self, base_url: str, max_depth: int = 1) -> AsyncGenerator[Set[str], None]:
        """Crawl starting at `base_url` up to `max_depth` levels.

        Depth semantics:
        - depth 0: the base_url itself
        - depth 1: pages linked directly from base_url
        If max_depth is 0, the crawler will only include the base_url and not fetch any links.
        """
        # queue holds tuples of (url, depth)
        queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
        seen_urls: Set[str] = {base_url}

        await queue.put((base_url, 0))
        async with aiohttp.ClientSession() as session:
            while not queue.empty():
                url, depth = await queue.get()
                content = await self._fetcher.fetch(session, url)
                if content is None:
                    continue

                # Only extract children when we haven't reached max_depth yet
                if depth < max_depth:
                    urls = get_urls_from_html(content, base_url)
                    unique_urls = [u for u in urls if u not in seen_urls]
                    valid_urls = [u for u in unique_urls if self.is_valid(u, base_url)]
                    for u in valid_urls:
                        await queue.put((u, depth + 1))
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