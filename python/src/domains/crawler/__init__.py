"""Public surface of the crawler domain."""

from domains.crawler.engine import Crawler
from domains.crawler.models import CrawlConfig, FetchResult, PageResult, ParseOutcome
from domains.crawler.parser import LinkParser

__all__ = [
    "CrawlConfig",
    "Crawler",
    "FetchResult",
    "LinkParser",
    "PageResult",
    "ParseOutcome",
]
