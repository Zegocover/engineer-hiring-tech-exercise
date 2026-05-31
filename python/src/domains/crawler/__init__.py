"""Public surface of the crawler domain."""

from domains.crawler.engine import Crawler
from domains.crawler.models import CrawlConfig, FetchResult, PageResult, ParseOutcome
from domains.crawler.robots import NoOpRobotsPolicy
from domains.crawler.stages.fetch_stage import DefaultFetchStage
from domains.crawler.stages.parse_stage import DefaultParseStage

__all__ = [
    "CrawlConfig",
    "Crawler",
    "DefaultFetchStage",
    "DefaultParseStage",
    "FetchResult",
    "NoOpRobotsPolicy",
    "PageResult",
    "ParseOutcome",
]
