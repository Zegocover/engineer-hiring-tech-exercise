"""In-memory components for exercising the crawler without a network."""

from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Mapping

from site_crawler.models import FetchError, FetchResult, PageResult


class FakeSite:
    """A fetcher serving pages from memory.

    Each page body is its hrefs, one per line (see :class:`LineParser`).
    """

    def __init__(
        self,
        pages: Mapping[str, list[str]],
        *,
        redirects: Mapping[str, str] | None = None,
        content_types: Mapping[str, str] | None = None,
        failing: set[str] | None = None,
        raw: Mapping[str, bytes] | None = None,
    ) -> None:
        self.pages = pages
        self.redirects = redirects or {}
        self.content_types = content_types or {}
        self.failing = failing or set()
        self.raw = raw or {}
        self.calls: Counter[str] = Counter()
        self.closed = 0

    async def fetch(self, url: str) -> FetchResult:
        self.calls[url] += 1
        await asyncio.sleep(0)  # let other workers interleave
        if url in self.failing:
            raise FetchError(url, "HTTP 500")
        final = self.redirects.get(url, url)
        content_type = self.content_types.get(final, "text/html; charset=utf-8")
        if final in self.raw:
            return FetchResult(url, final, 200, content_type, self.raw[final])
        if final not in self.pages:
            raise FetchError(url, "HTTP 404")
        body = "\n".join(self.pages[final]).encode()
        return FetchResult(url, final, 200, content_type, body)

    async def aclose(self) -> None:
        self.closed += 1


class LineParser:
    def parse(self, page: FetchResult) -> list[str]:
        return [line for line in page.body.decode().splitlines() if line]


class CollectingWriter:
    def __init__(self) -> None:
        self.results: list[PageResult] = []
        self.closed = 0

    async def write(self, result: PageResult) -> None:
        self.results.append(result)

    async def aclose(self) -> None:
        self.closed += 1

    def as_dict(self) -> dict[str, tuple[str, ...]]:
        return {r.url: r.links for r in self.results}
