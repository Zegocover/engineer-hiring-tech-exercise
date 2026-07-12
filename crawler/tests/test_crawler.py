from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from crawler.src.crawler import Crawler
from crawler.src.extractor import LinkContentExtractor
from crawler.src.fetcher import Fetcher
from crawler.src.filters import ExactDomainFilter
from crawler.src.frontier import Frontier
from crawler.src.normaliser import DefaultURLNormaliser

BASE_URL = "https://example.com/"

PAGES = {
    "/": """
        <a href="/a">A</a>
        <a href="/b">B</a>
        <a href="https://www.example.com/x">Subdomain</a>
        <a href="https://other.com/y">Other domain</a>
    """,
    "/a": '<a href="/b">B</a><a href="/">Home</a>',
    "/b": '<a href="/a">A</a><a href="/c">C</a>',
    "/c": "<p>no links here</p>",
}


def _html_response(path: str) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "text/html"}, text=PAGES[path])


@pytest.fixture
async def async_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        yield client


@pytest.mark.asyncio
async def test_crawl_stays_within_domain_and_visits_each_page_once(
    capsys: pytest.CaptureFixture[str], async_client: httpx.AsyncClient
) -> None:
    with respx.mock(base_url="https://example.com", assert_all_mocked=True) as mock:
        for path in PAGES:
            mock.get(path).mock(return_value=_html_response(path))

        fetcher = Fetcher(async_client)
        normaliser = DefaultURLNormaliser()
        crawler = Crawler(
            BASE_URL,
            fetcher=fetcher,
            frontier=Frontier(),
            normaliser=normaliser,
            content_extractor=LinkContentExtractor(normaliser),
            domain_filter=ExactDomainFilter(BASE_URL),
            concurrency=3,
        )
        stats = await crawler.run()

    assert stats.pages_crawled == 4
    assert stats.errors == 0

