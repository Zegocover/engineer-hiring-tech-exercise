"""Immutable value objects passed between the crawler's components."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FetchResult:
    """The outcome of a single HTTP fetch.

    ``error`` is set only for transport-level failures (timeouts, connection
    errors); an HTTP error *status* (e.g. 404, 500) is reported via
    ``status_code`` with ``error`` left ``None``. ``text`` is populated only when
    the response is HTML and worth parsing — see :class:`crawler.fetcher.Fetcher`.
    """

    requested_url: str
    final_url: str
    status_code: int | None = None
    content_type: str | None = None
    text: str | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        """True when the fetch succeeded with a non-error HTTP status."""
        return self.error is None and self.status_code is not None and self.status_code < 400


@dataclass(frozen=True, slots=True)
class PageResult:
    """A crawled page: its URL and every link discovered on it.

    ``links`` contains *all* links found (including off-domain ones), resolved to
    absolute URLs, in document order with in-page duplicates removed. The crawler
    decides separately which of those links to follow.
    """

    url: str
    links: tuple[str, ...]
    status_code: int | None = None
    error: str | None = None
