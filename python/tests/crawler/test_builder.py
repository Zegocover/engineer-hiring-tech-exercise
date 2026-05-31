import httpx

from crawler.builder import build_crawler
from domains.crawler.engine import Crawler
from domains.crawler.models import CrawlConfig


async def test_build_crawler_returns_wired_crawler() -> None:
    config = CrawlConfig(seed_url="http://a.com/", seed_host="a.com")
    async with httpx.AsyncClient() as client:
        crawler = build_crawler(config, client)
    assert isinstance(crawler, Crawler)
