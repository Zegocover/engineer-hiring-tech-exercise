from domains.crawler.engine import Crawler
from domains.crawler.models import CrawlConfig, FetchResult
from domains.crawler.robots import NoOpRobotsPolicy
from domains.crawler.stages.fetch_stage import DefaultFetchStage
from domains.crawler.stages.parse_stage import DefaultParseStage
from gateways.memory.queue import InMemoryQueue


class FakeFetcher:
    """Serves HTML from an in-memory {url: html} graph; 404s unknown URLs."""

    def __init__(self, pages: dict[str, str]) -> None:
        self._pages = pages

    async def fetch(self, url: str) -> FetchResult:
        if url in self._pages:
            return FetchResult(
                requested_url=url,
                final_url=url,
                status=200,
                content_type="text/html",
                html=self._pages[url],
                error=None,
            )
        return FetchResult(
            requested_url=url,
            final_url=url,
            status=404,
            content_type=None,
            html=None,
            error="not found",
        )


def _build(pages: dict[str, str], seed: str, max_pages: int | None = None) -> Crawler:
    config = CrawlConfig(seed_url=seed, seed_host="a.com", concurrency=3, max_pages=max_pages)
    fetch_stage = DefaultFetchStage(fetcher=FakeFetcher(pages), robots=NoOpRobotsPolicy())
    parse_stage = DefaultParseStage(seed_host="a.com")
    return Crawler(
        config=config,
        fetch_stage=fetch_stage,
        parse_stage=parse_stage,
        frontier=InMemoryQueue(),
        results=InMemoryQueue(),
    )


async def _run(crawler: Crawler) -> dict[str, list[str]]:
    return {pr.url: list(pr.links) async for pr in crawler.crawl()}


async def test_crawls_linked_pages_within_host() -> None:
    pages = {
        "http://a.com/": '<a href="/p1">1</a><a href="/p2">2</a>',
        "http://a.com/p1": '<a href="/p2">2</a>',
        "http://a.com/p2": "no links",
    }
    out = await _run(_build(pages, "http://a.com/"))
    assert set(out) == {"http://a.com/", "http://a.com/p1", "http://a.com/p2"}


async def test_each_page_emitted_exactly_once_with_cycle() -> None:
    pages = {
        "http://a.com/": '<a href="/p1">1</a>',
        "http://a.com/p1": '<a href="/">home</a>',  # cycle back to root
    }
    seen: list[str] = []
    crawler = _build(pages, "http://a.com/")
    async for pr in crawler.crawl():
        seen.append(pr.url)
    assert sorted(seen) == ["http://a.com/", "http://a.com/p1"]
    assert len(seen) == 2  # cycle did not cause a re-emit


async def test_offsite_and_subdomain_links_listed_not_followed() -> None:
    pages = {
        "http://a.com/": '<a href="http://b.com/x">b</a><a href="http://www.a.com/y">w</a>',
    }
    out = await _run(_build(pages, "http://a.com/"))
    # Only the seed page is crawled (no on-host links to follow)...
    assert set(out) == {"http://a.com/"}
    # ...but the off-site + subdomain links are still reported on it.
    assert out["http://a.com/"] == ["http://b.com/x", "http://www.a.com/y"]


async def test_fetch_error_is_recorded_not_fatal() -> None:
    pages = {
        "http://a.com/": '<a href="/missing">x</a>',
        # /missing is absent -> FakeFetcher returns a 404 error result
    }
    results = {}
    crawler = _build(pages, "http://a.com/")
    async for pr in crawler.crawl():
        results[pr.url] = pr
    assert set(results) == {"http://a.com/", "http://a.com/missing"}
    assert results["http://a.com/missing"].error == "not found"
    assert results["http://a.com/missing"].links == ()


async def test_max_pages_caps_the_crawl() -> None:
    pages = {
        "http://a.com/": '<a href="/p1">1</a><a href="/p2">2</a><a href="/p3">3</a>',
        "http://a.com/p1": "x",
        "http://a.com/p2": "x",
        "http://a.com/p3": "x",
    }
    out = await _run(_build(pages, "http://a.com/", max_pages=2))
    assert len(out) == 2  # seed + exactly one child, then capped
