"""In-memory sites and faulty storage, so jobs run without a network.

Pages are served as HTML ``<a href>`` lists because every job parses with
the library's real HTML parser (inside :class:`CachingParser`).
"""

from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from site_crawler.models import FetchError, FetchResult, PageResult

from crawl_daemon.models import JobStats
from crawl_daemon.storage import Storage

BASE = "https://example.com/"


def html(hrefs: Sequence[str]) -> bytes:
    return "".join(f'<a href="{href}">x</a>' for href in hrefs).encode()


class FakeSite:
    """Serves ``pages`` (URL -> hrefs) as HTML. Unknown URLs are 404s.

    URLs in ``failing`` raise :class:`FetchError`; URLs in ``broken`` raise an
    unexpected exception, as a buggy component would. ``robots.txt`` is a 404,
    which allows everything.
    """

    def __init__(
        self,
        pages: Mapping[str, Sequence[str]],
        *,
        failing: set[str] | None = None,
        broken: set[str] | None = None,
        text: Mapping[str, bytes] | None = None,
    ) -> None:
        self.pages = dict(pages)
        self.failing = failing or set()
        self.broken = broken or set()
        self.text = dict(text or {})
        self.calls: Counter[str] = Counter()

    async def fetch(self, url: str) -> FetchResult:
        self.calls[url] += 1
        await asyncio.sleep(0)  # let other tasks interleave
        if url in self.broken:
            raise RuntimeError(f"bug while fetching {url}")
        if url in self.failing:
            raise FetchError(url, "HTTP 500")
        if url in self.text:
            return FetchResult(url, url, 200, "text/plain", self.text[url])
        if url not in self.pages:
            raise FetchError(url, "HTTP 404")
        return FetchResult(url, url, 200, "text/html; charset=utf-8", html(self.pages[url]))

    async def aclose(self) -> None:
        pass


class GatedSite(FakeSite):
    """A :class:`FakeSite` whose ``gated`` URLs block until :attr:`gate` is set."""

    def __init__(self, pages: Mapping[str, Sequence[str]], *, gated: set[str]) -> None:
        super().__init__(pages)
        self.gated = gated
        self.gate = asyncio.Event()

    async def fetch(self, url: str) -> FetchResult:
        if url in self.gated:
            await self.gate.wait()
        return await super().fetch(url)


def chain_site(count: int, base: str = BASE) -> dict[str, list[str]]:
    """``count`` pages: the base links to /1, /1 to /2, and so on."""
    urls = [base, *(f"{base}{i}" for i in range(1, count))]
    return {url: urls[i + 1 : i + 2] for i, url in enumerate(urls)}


class FaultyStorage:
    """Wraps a storage; methods named in ``failing`` raise instead."""

    def __init__(self, inner: Storage, *failing: str) -> None:
        self.inner = inner
        self.failing = set(failing)
        self.calls: Counter[str] = Counter()

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self.inner, name)
        if not callable(attr):
            return attr

        async def call(*args: Any, **kwargs: Any) -> Any:
            self.calls[name] += 1
            if name in self.failing:
                raise RuntimeError(f"{name} failed")
            return await attr(*args, **kwargs)

        return call


class MemoryStorage:
    """Just enough storage for the components' unit tests."""

    def __init__(self) -> None:
        self.pages: list[tuple[str, int, PageResult]] = []
        self.links: list[tuple[str, int, str]] = []
        self.stats: list[JobStats] = []
        self.cache: dict[str, list[str]] = {}
        self.lookups: list[list[str]] = []

    async def append_results(
        self,
        job_id: str,
        pages: Sequence[tuple[int, PageResult]],
        links: Sequence[tuple[int, str]],
        stats: JobStats,
    ) -> None:
        self.pages += [(job_id, seq, page) for seq, page in pages]
        self.links += [(job_id, seq, url) for seq, url in links]
        self.stats.append(stats)

    async def get_parsed_links(self, keys: Sequence[str]) -> dict[str, list[str]]:
        self.lookups.append(list(keys))
        return {key: self.cache[key] for key in keys if key in self.cache}

    async def put_parsed_links(
        self, entries: Sequence[tuple[str, list[str]]], at: datetime
    ) -> None:
        for key, links in entries:
            self.cache.setdefault(key, links)
