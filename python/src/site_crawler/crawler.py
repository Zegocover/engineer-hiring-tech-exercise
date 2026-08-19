from collections.abc import AsyncIterator
from typing import Protocol

from site_crawler.models import PageLinks


class HttpClient(Protocol):
    async def get(self, url: str) -> object:
        """Fetch a URL using a pooled asynchronous HTTP client."""


class Crawler:
    """Coordinates bounded, exact-domain page traversal.

    Network traversal is intentionally left for the implementation phase. The
    transport is represented by a protocol so tests can use an in-memory fake.
    """

    def __init__(self, client: HttpClient) -> None:
        self._client = client

    async def crawl(self, base_url: str) -> AsyncIterator[PageLinks]:
        """Yield pages discovered once traversal is implemented."""
        del self._client, base_url
        raise NotImplementedError("crawler traversal is not implemented yet")
        yield
