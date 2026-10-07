"""Fast single-host web crawler with pluggable fetch, parse and write components.

Package layout (each layer only imports the ones before it):

- ``models``      data exchanged between components (results, config, stats, errors)
- ``interfaces``  the protocols consumers implement: Fetcher, Parser, Writer
- ``fetchers``, ``parsers``, ``writers``  the default implementations
- ``core``        the crawl engine
"""

from site_crawler.core import Crawler
from site_crawler.fetchers import DefaultHttpxFetcher
from site_crawler.interfaces import Fetcher, Parser, Writer
from site_crawler.models import (
    ConfigError,
    CrawlConfig,
    CrawlStats,
    FetchError,
    FetchResult,
    PageResult,
)
from site_crawler.parsers import DefaultSelectolaxParser
from site_crawler.writers import JsonLinesWriter, TextWriter

__all__ = [
    "ConfigError",
    "CrawlConfig",
    "CrawlStats",
    "Crawler",
    "DefaultHttpxFetcher",
    "DefaultSelectolaxParser",
    "FetchError",
    "FetchResult",
    "Fetcher",
    "JsonLinesWriter",
    "PageResult",
    "Parser",
    "TextWriter",
    "Writer",
]
