"""The daemon's fetcher: one shared HTTP client, plus the parse cache lookup."""

from __future__ import annotations

import logging

import httpx
from site_crawler import DefaultHttpxFetcher
from site_crawler.interfaces import Fetcher
from site_crawler.models import FetchResult

from crawl_daemon.components.parser import ParseCache, cache_key
from crawl_daemon.storage import Storage

logger = logging.getLogger(__name__)


class SharedClientFetcher:
    """Fetches through a fetcher the daemon owns, and prefetches cached parses.

    Retries, body capping and error mapping come from the inner fetcher,
    normally the library's default over the daemon's shared
    ``httpx.AsyncClient`` (see :meth:`for_client`). ``aclose`` does nothing:
    the crawler closes its fetcher when the crawl ends, but the client belongs
    to the daemon and serves every other job too.

    After an HTML page is fetched, its parse is looked up in storage here,
    where awaiting is possible, so the synchronous parser never waits on the
    database. A failed lookup is logged and the page is simply parsed.
    """

    def __init__(self, inner: Fetcher, *, storage: Storage, cache: ParseCache) -> None:
        self._inner = inner
        self._storage = storage
        self._cache = cache

    @classmethod
    def for_client(
        cls, client: httpx.AsyncClient, *, storage: Storage, cache: ParseCache
    ) -> SharedClientFetcher:
        return cls(DefaultHttpxFetcher(client=client), storage=storage, cache=cache)

    async def fetch(self, url: str) -> FetchResult:
        result = await self._inner.fetch(url)
        if self._cache.enabled and result.is_html:
            try:
                key = cache_key(result)
                found = await self._storage.get_parsed_links([key])
            except Exception:
                logger.warning("parse cache lookup failed for %s", url, exc_info=True)
            else:
                if key in found:
                    self._cache.prefetched[key] = found[key]
        return result

    async def aclose(self) -> None:
        pass
