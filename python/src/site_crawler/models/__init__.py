"""Data models exchanged between the crawler and its components."""

from site_crawler.models.config import DEFAULT_USER_AGENT, ConfigError, CrawlConfig
from site_crawler.models.errors import FetchError
from site_crawler.models.fetch import FetchResult
from site_crawler.models.page import PageResult
from site_crawler.models.stats import CrawlStats

__all__ = [
    "DEFAULT_USER_AGENT",
    "ConfigError",
    "CrawlConfig",
    "CrawlStats",
    "FetchError",
    "FetchResult",
    "PageResult",
]
