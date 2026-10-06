from __future__ import annotations

import asyncio

import pytest

from site_crawler.core import Crawler
from site_crawler.models import CrawlConfig, FetchResult, PageResult
from tests.fakes import CollectingWriter, FakeSite, LineParser

BASE = "https://example.com/"
PAGES = {
    BASE: ["/a", "/broken", "/b"],
    "https://example.com/a": [],
    "https://example.com/b": [],
}


async def test_fetch_error_recorded_and_crawl_continues() -> None:
    site = FakeSite(PAGES, failing={"https://example.com/broken"})
    writer = CollectingWriter()
    stats = await Crawler(CrawlConfig(BASE), fetcher=site, parser=LineParser(), writer=writer).run()
    assert set(writer.as_dict()) == {BASE, "https://example.com/a", "https://example.com/b"}
    assert stats.errors == 1
    assert stats.error_urls == ["https://example.com/broken"]
    assert stats.pages == 3


async def test_seed_failure_reported() -> None:
    site = FakeSite({}, failing={BASE})
    stats = await Crawler(
        CrawlConfig(BASE), fetcher=site, parser=LineParser(), writer=CollectingWriter()
    ).run()
    assert not stats.seed_ok
    assert stats.errors == 1


class BuggyParser:
    def parse(self, page: FetchResult) -> list[str]:
        if page.final_url.endswith("/a"):
            raise RuntimeError("parser bug")
        return LineParser().parse(page)


async def test_unexpected_parser_error_propagates_after_closing() -> None:
    site = FakeSite(PAGES)
    writer = CollectingWriter()
    crawler = Crawler(CrawlConfig(BASE), fetcher=site, parser=BuggyParser(), writer=writer)
    with pytest.raises(RuntimeError, match="parser bug"):
        await asyncio.wait_for(crawler.run(), timeout=5)
    assert writer.closed == 1
    assert site.closed == 1


class FailingWriter(CollectingWriter):
    async def write(self, result: PageResult) -> None:
        raise OSError("disk full")


async def test_unexpected_writer_error_propagates() -> None:
    writer = FailingWriter()
    crawler = Crawler(
        CrawlConfig(BASE), fetcher=FakeSite(PAGES), parser=LineParser(), writer=writer
    )
    with pytest.raises(OSError, match="disk full"):
        await asyncio.wait_for(crawler.run(), timeout=5)
    assert writer.closed == 1


class ExplodingFetcher(FakeSite):
    async def fetch(self, url: str) -> FetchResult:
        if url.endswith("/b"):
            raise KeyError("boom")
        return await super().fetch(url)


async def test_unexpected_fetcher_error_does_not_hang() -> None:
    site = ExplodingFetcher(PAGES)
    crawler = Crawler(
        CrawlConfig(BASE, concurrency=1),
        fetcher=site,
        parser=LineParser(),
        writer=CollectingWriter(),
    )
    with pytest.raises(KeyError):
        await asyncio.wait_for(crawler.run(), timeout=5)
    assert site.closed == 1
