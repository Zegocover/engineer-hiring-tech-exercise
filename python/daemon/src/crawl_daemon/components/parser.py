"""A parser that reuses links already parsed from identical pages.

The library's :class:`~site_crawler.interfaces.Parser` is synchronous and runs
on the event loop, so it can't await a database. Instead the job's fetcher
looks each HTML page up while it is still async (see
:class:`~crawl_daemon.components.fetcher.SharedClientFetcher`) and leaves any
hit in the job's :class:`ParseCache`; the parser only touches that dict. New
results queue in the cache until the writer stores them.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field

from site_crawler.interfaces import Parser
from site_crawler.models import FetchResult
from site_crawler.parsers import DefaultSelectolaxParser

logger = logging.getLogger(__name__)

PARSER_VERSION = "selectolax-1"
"""Part of every cache key: change it whenever the inner parser's output could change."""


def cache_key(page: FetchResult, version: str = PARSER_VERSION) -> str:
    """Identify a parse: the parser, the URL links resolve against, and the body."""
    digest = hashlib.sha256()
    for part in (version.encode(), page.final_url.encode(), page.body):
        digest.update(len(part).to_bytes(8, "big"))  # unambiguous boundaries
        digest.update(part)
    return digest.hexdigest()


@dataclass(slots=True)
class ParseCache:
    """One job's view of the parse cache, shared by its fetcher, parser and writer."""

    enabled: bool = True
    prefetched: dict[str, list[str]] = field(default_factory=dict)
    """Cached links the fetcher found, waiting for the parser."""
    pending: list[tuple[str, list[str]]] = field(default_factory=list)
    """Fresh parses waiting for the writer to store them."""
    hits: int = 0

    def take(self, key: str) -> list[str] | None:
        return self.prefetched.pop(key, None)

    def add(self, key: str, links: list[str]) -> None:
        if self.enabled:
            self.pending.append((key, links))

    def drain(self) -> list[tuple[str, list[str]]]:
        entries, self.pending = self.pending, []
        return entries


class CachingParser:
    """Wraps a parser (the library's selectolax parser by default) with the parse cache."""

    def __init__(self, cache: ParseCache, inner: Parser | None = None) -> None:
        self._cache = cache
        self._inner = inner or DefaultSelectolaxParser()

    def parse(self, page: FetchResult) -> list[str]:
        cache = self._cache
        if not cache.enabled:
            return self._inner.parse(page)
        try:
            key = cache_key(page)
            cached = cache.take(key)
        except Exception:
            logger.warning("parse cache unavailable for %s", page.final_url, exc_info=True)
            return self._inner.parse(page)
        if cached is not None:
            cache.hits += 1
            return list(cached)
        links = self._inner.parse(page)
        try:
            cache.add(key, list(links))
        except Exception:
            logger.warning("could not queue %s for the parse cache", page.final_url, exc_info=True)
        return links
