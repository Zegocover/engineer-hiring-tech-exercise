"""Default :class:`~site_crawler.interfaces.Fetcher` implementations."""

from site_crawler.fetchers.httpx_fetcher import HttpxFetcher

__all__ = ["HttpxFetcher"]
