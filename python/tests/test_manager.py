from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from site_crawler.core import Crawler
from site_crawler.models import CrawlConfig, CrawlStats
from tests.fakes import CollectingWriter, FakeSite, LineParser

BASE = "https://example.com/"


async def crawl(
    pages: Mapping[str, list[str]], *, site_kwargs: Mapping[str, Any] | None = None, **config: Any
) -> tuple[FakeSite, CollectingWriter, CrawlStats]:
    config.setdefault("respect_robots", False)
    site = FakeSite(pages, **(site_kwargs or {}))
    writer = CollectingWriter()
    crawler = Crawler(CrawlConfig(BASE, **config), fetcher=site, parser=LineParser(), writer=writer)
    stats = await crawler.run()
    return site, writer, stats


async def test_cyclic_links_fetched_once_and_terminates() -> None:
    site, writer, stats = await crawl({BASE: ["/b"], "https://example.com/b": ["/"]})
    assert site.calls == {BASE: 1, "https://example.com/b": 1}
    assert writer.as_dict() == {
        BASE: ("https://example.com/b",),
        "https://example.com/b": (BASE,),
    }
    assert stats.pages == 2
    assert stats.seed_ok


async def test_links_deduplicated_in_document_order() -> None:
    _, writer, _ = await crawl(
        {
            BASE: ["/a", "/a", "https://other.org/", "/b", "/a#frag"],
            "https://example.com/a": [],
            "https://example.com/b": [],
        }
    )
    assert writer.as_dict()[BASE] == (
        "https://example.com/a",
        "https://other.org/",
        "https://example.com/b",
    )


async def test_off_host_links_reported_not_fetched() -> None:
    site, writer, _ = await crawl(
        {BASE: ["https://other.org/", "https://www.example.com/", "https://blog.example.com/x"]}
    )
    assert set(site.calls) == {BASE}
    assert writer.as_dict()[BASE] == (
        "https://other.org/",
        "https://www.example.com/",
        "https://blog.example.com/x",
    )


async def test_non_http_links_ignored() -> None:
    _, writer, _ = await crawl({BASE: ["mailto:hi@example.com", "javascript:void(0)", "tel:1"]})
    assert writer.as_dict() == {BASE: ()}


async def test_page_with_no_links_is_reported() -> None:
    _, writer, stats = await crawl({BASE: []})
    assert writer.as_dict() == {BASE: ()}
    assert stats.pages == 1


async def test_shared_link_fetched_once_under_concurrency() -> None:
    pages = {BASE: [f"/p{i}" for i in range(50)]}
    for i in range(50):
        pages[f"https://example.com/p{i}"] = ["/shared", "/"]
    pages["https://example.com/shared"] = []
    site, writer, stats = await crawl(pages, concurrency=16)
    assert max(site.calls.values()) == 1
    assert stats.pages == 52
    assert len({r.url for r in writer.results}) == 52


async def test_max_pages_limits_fetches() -> None:
    pages = {BASE: [f"/p{i}" for i in range(100)]}
    pages.update({f"https://example.com/p{i}": [] for i in range(100)})
    site, _, stats = await crawl(pages, max_pages=10)
    assert sum(site.calls.values()) == 10
    assert stats.pages == 10


async def test_max_depth_limits_crawl() -> None:
    pages = {
        BASE: ["/d1"],
        "https://example.com/d1": ["/d2"],
        "https://example.com/d2": ["/d3"],
        "https://example.com/d3": [],
    }
    site, _, _ = await crawl(pages, max_depth=1)
    assert set(site.calls) == {BASE, "https://example.com/d1"}


async def test_max_depth_zero_fetches_only_seed() -> None:
    site, writer, _ = await crawl({BASE: ["/a"], "https://example.com/a": []}, max_depth=0)
    assert set(site.calls) == {BASE}
    assert writer.as_dict() == {BASE: ("https://example.com/a",)}


async def test_writer_closed_once_and_fetcher_closed() -> None:
    site, writer, _ = await crawl({BASE: []})
    assert writer.closed == 1
    assert site.closed == 1


async def test_relative_links_resolve_against_redirect_target() -> None:
    _, writer, _ = await crawl(
        {BASE: ["/old"], "https://example.com/new/": ["page"], "https://example.com/new/page": []},
        site_kwargs={"redirects": {"https://example.com/old": "https://example.com/new/"}},
    )
    results = writer.as_dict()
    assert results["https://example.com/new/"] == ("https://example.com/new/page",)
    assert "https://example.com/new/page" in results


async def test_redirect_to_already_seen_page_not_reported_twice() -> None:
    _, writer, _ = await crawl(
        {BASE: ["/new", "/old"], "https://example.com/new": []},
        site_kwargs={"redirects": {"https://example.com/old": "https://example.com/new"}},
    )
    assert [r.url for r in writer.results].count("https://example.com/new") == 1


async def test_off_host_redirect_dropped() -> None:
    site, writer, stats = await crawl(
        {BASE: ["/go"], "https://other.org/": ["/secret"]},
        site_kwargs={"redirects": {"https://example.com/go": "https://other.org/"}},
    )
    assert set(writer.as_dict()) == {BASE}
    assert "https://other.org/secret" not in site.calls
    assert stats.fetched == 2


async def test_non_html_fetched_once_not_parsed_or_reported() -> None:
    pdf = "https://example.com/doc.pdf"
    site, writer, stats = await crawl(
        {BASE: ["/doc.pdf", "/doc.pdf"]},
        site_kwargs={
            "raw": {pdf: b"/should-not-be-followed"},
            "content_types": {pdf: "application/pdf"},
        },
    )
    assert site.calls[pdf] == 1
    assert "https://example.com/should-not-be-followed" not in site.calls
    assert set(writer.as_dict()) == {BASE}
    assert stats.pages == 1
