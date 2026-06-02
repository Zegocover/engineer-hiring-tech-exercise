import httpx

from crawler.factory import crawler_factory
from domains.crawler.engine import Crawler
from domains.crawler.models import CrawlConfig


async def test_crawler_factory_returns_wired_crawler() -> None:
    config = CrawlConfig(seed_url="http://a.com/", seed_host="a.com")
    async with httpx.AsyncClient() as client:
        crawler = crawler_factory(config, client)
    assert isinstance(crawler, Crawler)
