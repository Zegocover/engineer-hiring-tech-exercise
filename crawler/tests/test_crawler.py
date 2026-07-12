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


class AllowAllRobotsPolicy:
    crawl_delay: float | None = None

    def is_allowed(self, url: str) -> bool:
        return True


class DisallowRobotsPolicy:
    crawl_delay: float | None = None

    def __init__(self, disallowed_url: str) -> None:
        self._disallowed_url = disallowed_url

    def is_allowed(self, url: str) -> bool:
        return url != self._disallowed_url


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
            robots_policy=AllowAllRobotsPolicy(),
        )
        stats = await crawler.run()

    assert stats.pages_crawled == 4
    assert stats.errors == 0


@pytest.mark.asyncio
async def test_robots_disallowed_pages_are_skipped_and_counted(
    capsys: pytest.CaptureFixture[str], async_client: httpx.AsyncClient
) -> None:
    # "/c" isn't registered as a mocked route. If the crawler ever
    # tried to fetch it despite robots.txt disallowing it, respx would raise an
    # `unmocked-request` error and fail this test.
    with respx.mock(base_url="https://example.com", assert_all_mocked=True) as mock:
        for path in ("/", "/a", "/b"):
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
            robots_policy=DisallowRobotsPolicy("https://example.com/c"),
            concurrency=3,
        )
        stats = await crawler.run()

    assert stats.pages_crawled == 3
    assert stats.errors == 0
