import asyncio

import pytest

from site_crawler.crawler import Crawler


class FakeClient:
    async def get(self, url: str) -> object:
        return url


def test_crawler_exposes_async_traversal_boundary() -> None:
    crawler = Crawler(FakeClient())

    async def run_crawl() -> None:
        with pytest.raises(NotImplementedError, match="not implemented"):
            async for _ in crawler.crawl("https://example.test"):
                pass

    asyncio.run(run_crawl())
