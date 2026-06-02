import httpx
from pytest_httpx import HTTPXMock

from crawler.factory import crawler_factory
from domains.crawler.models import CrawlConfig, PageResult


async def test_real_stack_crawls_small_site(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="http://site.test/",
        html='<a href="/about">about</a><a href="http://other.test/x">ext</a>',
        headers={"content-type": "text/html"},
    )
    httpx_mock.add_response(
        url="http://site.test/about",
        html='<a href="/">home</a>',
        headers={"content-type": "text/html"},
    )

    config = CrawlConfig(seed_url="http://site.test/", seed_host="site.test")
    pages: dict[str, PageResult] = {}
    async with httpx.AsyncClient() as client:
        crawler = crawler_factory(config, client)
        async for page in crawler.crawl():
            pages[page.url] = page

    assert set(pages) == {"http://site.test/", "http://site.test/about"}
    # External link listed on the home page but not followed.
    assert "http://other.test/x" in pages["http://site.test/"].links
    assert "http://other.test/" not in pages
