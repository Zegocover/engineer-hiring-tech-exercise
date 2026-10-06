from __future__ import annotations

from typing import Protocol

from site_crawler.models import FetchResult


class Fetcher(Protocol):
    """Retrieves a URL.

    Raise :class:`site_crawler.models.FetchError` when the URL can't be
    retrieved; the crawler records it and carries on.
    """

    async def fetch(self, url: str) -> FetchResult: ...

    async def aclose(self) -> None: ...
