import asyncio
import logging
from typing import cast

import httpx
import pytest
import respx
from site_crawler.interfaces import Fetcher, Parser, Writer
from site_crawler.models import FetchResult, PageResult
from site_crawler.parsers import DefaultSelectolaxParser

from crawl_daemon.components import (
    PARSER_VERSION,
    CachingParser,
    ParseCache,
    SharedClientFetcher,
    StorageWriteError,
    StorageWriter,
    cache_key,
)
from crawl_daemon.models import JobStats
from crawl_daemon.storage import Storage
from tests.fakes import FakeSite, MemoryStorage, html

URL = "https://example.com/"
PAGE = FetchResult(URL, URL, 200, "text/html", html(["/a", "/b", "https://other.org/"]))


def as_storage(storage: MemoryStorage) -> Storage:
    return cast(Storage, storage)


# --- protocols -------------------------------------------------------------------------


def test_components_satisfy_library_protocols() -> None:
    cache = ParseCache()
    storage = as_storage(MemoryStorage())
    _fetcher: Fetcher = SharedClientFetcher(FakeSite({}), storage=storage, cache=cache)
    _parser: Parser = CachingParser(cache)
    _writer: Writer = StorageWriter(storage, "j", stats=JobStats, cache=cache)


# --- cache keys ------------------------------------------------------------------------


def test_cache_key_depends_on_body_final_url_and_version() -> None:
    key = cache_key(PAGE)
    assert key == cache_key(FetchResult("https://x/", URL, 200, "text/html", PAGE.body))
    assert key != cache_key(FetchResult(URL, URL, 200, "text/html", PAGE.body + b" "))
    assert key != cache_key(FetchResult(URL, URL + "index", 200, "text/html", PAGE.body))
    assert key != cache_key(PAGE, PARSER_VERSION + "-next")


# --- parser ----------------------------------------------------------------------------


def test_miss_parses_and_queues() -> None:
    cache = ParseCache()
    links = CachingParser(cache).parse(PAGE)
    assert links == DefaultSelectolaxParser().parse(PAGE)
    assert cache.pending == [(cache_key(PAGE), links)]
    assert cache.hits == 0


def test_hit_uses_prefetched_links_once() -> None:
    cache = ParseCache(prefetched={cache_key(PAGE): ["/cached"]})
    parser = CachingParser(cache)
    assert parser.parse(PAGE) == ["/cached"]
    assert cache.hits == 1
    assert cache.pending == []
    assert parser.parse(PAGE) == DefaultSelectolaxParser().parse(PAGE)  # consumed: parsed now
    assert cache.hits == 1


def test_changed_page_misses() -> None:
    cache = ParseCache(prefetched={cache_key(PAGE): ["/old"]})
    changed = FetchResult(URL, URL, 200, "text/html", html(["/new"]))
    assert CachingParser(cache).parse(changed) == ["/new"]
    assert cache.hits == 0


def test_cache_error_falls_back_to_parsing() -> None:
    class BrokenCache(ParseCache):
        def take(self, key: str) -> list[str] | None:
            raise RuntimeError("boom")

    cache = BrokenCache()
    assert CachingParser(cache).parse(PAGE) == DefaultSelectolaxParser().parse(PAGE)
    assert cache.hits == 0


def test_disabled_cache_never_queues_or_hits() -> None:
    cache = ParseCache(enabled=False, prefetched={cache_key(PAGE): ["/cached"]})
    assert CachingParser(cache).parse(PAGE) == DefaultSelectolaxParser().parse(PAGE)
    assert (cache.hits, cache.pending) == (0, [])


# --- fetcher ---------------------------------------------------------------------------


@respx.mock
async def test_fetcher_uses_shared_client_and_leaves_it_open() -> None:
    respx.get(URL).respond(200, html=PAGE.body.decode())
    async with httpx.AsyncClient() as client:
        fetcher = SharedClientFetcher.for_client(
            client, storage=as_storage(MemoryStorage()), cache=ParseCache()
        )
        result = await fetcher.fetch(URL)
        await fetcher.aclose()
        assert not client.is_closed
    assert result.body == PAGE.body


@respx.mock
async def test_fetcher_prefetches_cached_parse() -> None:
    respx.get(URL).respond(200, html=PAGE.body.decode())
    storage = MemoryStorage()
    key = cache_key(PAGE)
    storage.cache[key] = ["/cached"]
    cache = ParseCache()
    async with httpx.AsyncClient() as client:
        fetcher = SharedClientFetcher.for_client(client, storage=as_storage(storage), cache=cache)
        await fetcher.fetch(URL)
    assert cache.prefetched == {key: ["/cached"]}


async def test_fetcher_skips_lookup_for_non_html_and_disabled_cache() -> None:
    site = FakeSite({URL: ["/a"]}, text={URL + "robots.txt": b"User-agent: *"})
    storage = MemoryStorage()
    await SharedClientFetcher(site, storage=as_storage(storage), cache=ParseCache()).fetch(
        URL + "robots.txt"
    )
    disabled = ParseCache(enabled=False)
    await SharedClientFetcher(site, storage=as_storage(storage), cache=disabled).fetch(URL)
    assert storage.lookups == []


async def test_failed_lookup_still_returns_page(caplog: pytest.LogCaptureFixture) -> None:
    class BrokenStorage(MemoryStorage):
        async def get_parsed_links(self, keys: object) -> dict[str, list[str]]:
            raise RuntimeError("database down")

    site = FakeSite({URL: ["/a"]})
    cache = ParseCache()
    fetcher = SharedClientFetcher(site, storage=as_storage(BrokenStorage()), cache=cache)
    with caplog.at_level(logging.WARNING):
        result = await fetcher.fetch(URL)
    assert result.url == URL
    assert cache.prefetched == {}
    assert "parse cache lookup failed" in caplog.text


# --- writer ----------------------------------------------------------------------------


def make_writer(
    storage: MemoryStorage, cache: ParseCache | None = None, **options: float
) -> StorageWriter:
    return StorageWriter(
        as_storage(storage),
        "j",
        stats=lambda: JobStats(pages=len(storage.pages)),
        cache=cache or ParseCache(),
        **options,  # type: ignore[arg-type]
    )


def page(n: int, *links: str) -> PageResult:
    return PageResult(f"{URL}{n}", links)


async def test_pages_readable_after_flush_interval() -> None:
    storage = MemoryStorage()
    writer = make_writer(storage, flush_interval=0.01)
    await writer.write(page(0, "/a"))
    assert storage.pages == []  # buffered
    await asyncio.sleep(0.2)
    assert storage.pages == [("j", 0, page(0, "/a"))]
    await writer.aclose()


async def test_full_batch_is_written_at_once() -> None:
    storage = MemoryStorage()
    writer = make_writer(storage, batch_size=3, flush_interval=60)
    for n in range(3):
        await writer.write(page(n))
    assert [seq for _, seq, _ in storage.pages] == [0, 1, 2]
    await writer.aclose()


async def test_every_page_stored_after_aclose_with_distinct_links() -> None:
    storage = MemoryStorage()
    writer = make_writer(storage, batch_size=2, flush_interval=60)
    await writer.write(page(0, "/a", "/b"))
    await writer.write(page(1, "/b", "/c"))
    await writer.write(page(2, "/a", "/d"))
    await writer.aclose()
    assert [seq for _, seq, _ in storage.pages] == [0, 1, 2]
    assert [(seq, url) for _, seq, url in storage.links] == [
        (0, "/a"),
        (1, "/b"),
        (2, "/c"),
        (3, "/d"),
    ]
    await writer.aclose()  # idempotent
    assert len(storage.pages) == 3


async def test_flush_saves_stats_and_cache_entries() -> None:
    storage = MemoryStorage()
    cache = ParseCache()
    cache.add("k", ["/x"])
    writer = make_writer(storage, cache)
    await writer.write(page(0))
    await writer.aclose()
    assert storage.cache == {"k": ["/x"]}
    assert cache.pending == []
    assert storage.stats[-1] == JobStats(pages=0)  # the snapshot taken before this batch


async def test_failing_page_write_raises() -> None:
    class BrokenStorage(MemoryStorage):
        async def append_results(self, *args: object) -> None:
            raise RuntimeError("disk full")

    writer = make_writer(BrokenStorage(), batch_size=1)
    with pytest.raises(StorageWriteError, match="disk full"):
        await writer.write(page(0))
    with pytest.raises(StorageWriteError):
        await writer.write(page(1))
    with pytest.raises(StorageWriteError):
        await writer.aclose()


async def test_failing_timed_flush_raises_from_aclose() -> None:
    class BrokenStorage(MemoryStorage):
        async def append_results(self, *args: object) -> None:
            raise RuntimeError("disk full")

    writer = make_writer(BrokenStorage(), flush_interval=0.01)
    await writer.write(page(0))
    await asyncio.sleep(0.05)
    with pytest.raises(StorageWriteError, match="disk full"):
        await writer.aclose()


async def test_failing_cache_write_is_only_logged(caplog: pytest.LogCaptureFixture) -> None:
    class BrokenCacheStorage(MemoryStorage):
        async def put_parsed_links(self, *args: object) -> None:
            raise RuntimeError("cache table locked")

    storage = BrokenCacheStorage()
    cache = ParseCache()
    cache.add("k", ["/x"])
    writer = make_writer(storage, cache)
    await writer.write(page(0))
    with caplog.at_level(logging.WARNING):
        await writer.aclose()
    assert len(storage.pages) == 1
    assert "parse cache entries" in caplog.text
