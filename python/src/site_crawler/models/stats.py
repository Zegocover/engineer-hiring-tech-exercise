from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CrawlStats:
    """Summary returned by :meth:`site_crawler.Crawler.run`."""

    pages: int = 0
    """Pages reported to the writer."""
    fetched: int = 0
    """Successful fetches, including non-HTML and off-host redirects."""
    errors: int = 0
    """URLs that failed with :class:`FetchError`."""
    robots_skipped: int = 0
    """Same-host URLs not fetched because robots.txt disallows them."""
    seed_ok: bool = False
    """Whether the base URL was fetched successfully."""
    error_urls: list[str] = field(default_factory=list)
