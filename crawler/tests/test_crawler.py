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


def _build_crawler(
    async_client: httpx.AsyncClient, *, max_pages: int | None = None, concurrency: int = 1
) -> Crawler:
    normaliser = DefaultURLNormaliser()
    return Crawler(
        BASE_URL,
        fetcher=Fetcher(async_client),
        frontier=Frontier(),
        normaliser=normaliser,
        content_extractor=LinkContentExtractor(normaliser),
        domain_filter=ExactDomainFilter(BASE_URL),
        robots_policy=AllowAllRobotsPolicy(),
        concurrency=concurrency,
        max_pages=max_pages,
    )


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


@pytest.mark.asyncio
async def test_max_pages_stops_crawl_once_reached(async_client: httpx.AsyncClient) -> None:
    # concurrency=1 keeps crawl order deterministic: "/" then "/a" reach the cap of 2,
    # so "/b" (queued but never fetched) and "/c" (never even discovered) must not be
    # requested -- if they were, respx would raise an unmocked-request error below.
    with respx.mock(base_url="https://example.com", assert_all_mocked=True) as mock:
        mock.get("/").mock(return_value=_html_response("/"))
        mock.get("/a").mock(return_value=_html_response("/a"))

        stats = await _build_crawler(async_client, max_pages=2).run()

    assert stats.pages_crawled == 2
    assert stats.errors == 0


@pytest.mark.asyncio
async def test_max_pages_zero_crawls_nothing(async_client: httpx.AsyncClient) -> None:
    with respx.mock(base_url="https://example.com", assert_all_mocked=True):
        stats = await _build_crawler(async_client, max_pages=0).run()

    assert stats.pages_crawled == 0
    assert stats.errors == 0


@pytest.mark.asyncio
async def test_max_pages_above_reachable_count_crawls_everything(
    async_client: httpx.AsyncClient,
) -> None:
    with respx.mock(base_url="https://example.com", assert_all_mocked=True) as mock:
        for path in PAGES:
            mock.get(path).mock(return_value=_html_response(path))

        stats = await _build_crawler(async_client, max_pages=100).run()

    assert stats.pages_crawled == 4
    assert stats.errors == 0


@pytest.mark.asyncio
async def test_max_pages_none_means_unlimited(async_client: httpx.AsyncClient) -> None:
    with respx.mock(base_url="https://example.com", assert_all_mocked=True) as mock:
        for path in PAGES:
            mock.get(path).mock(return_value=_html_response(path))

        stats = await _build_crawler(async_client, max_pages=None).run()

    assert stats.pages_crawled == 4
    assert stats.errors == 0
