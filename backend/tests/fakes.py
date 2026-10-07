"""In-memory fetchers so crawls run without a network.

Pages are served as HTML ``<a href>`` lists because the service always uses
the library's real HTML parser.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Mapping

from site_crawler.models import FetchError, FetchResult


def html(hrefs: list[str]) -> bytes:
    return "".join(f'<a href="{href}">x</a>' for href in hrefs).encode()


class FakeSite:
    """Serves ``pages`` (URL -> hrefs). Unknown URLs are 404s.

    URLs in ``failing`` raise :class:`FetchError`; URLs in ``broken`` raise
    an unexpected exception, as a buggy component would.
    """

    def __init__(
        self,
        pages: Mapping[str, list[str]],
        *,
        failing: set[str] | None = None,
        broken: set[str] | None = None,
    ) -> None:
        self.pages = pages
        self.failing = failing or set()
        self.broken = broken or set()
        self.calls: Counter[str] = Counter()

    async def fetch(self, url: str) -> FetchResult:
        self.calls[url] += 1
        await asyncio.sleep(0)  # let other tasks interleave
        if url in self.broken:
            raise RuntimeError(f"bug while fetching {url}")
        if url in self.failing:
            raise FetchError(url, "HTTP 500")
        if url not in self.pages:
            raise FetchError(url, "HTTP 404")
        return FetchResult(url, url, 200, "text/html; charset=utf-8", html(self.pages[url]))

    async def aclose(self) -> None:
        pass


class GatedSite(FakeSite):
    """A :class:`FakeSite` whose ``gated`` URLs block until :attr:`gate` is set.

    Lets tests hold a crawl in the ``running`` state for as long as they need.
    """

    def __init__(self, pages: Mapping[str, list[str]], *, gated: set[str]) -> None:
        super().__init__(pages)
        self.gated = gated
        self.gate = asyncio.Event()

    async def fetch(self, url: str) -> FetchResult:
        if url in self.gated:
            await self.gate.wait()
        return await super().fetch(url)
