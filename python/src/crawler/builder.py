"""Composition root wiring: assemble a Crawler from config + an httpx client."""

import httpx

from domains.crawler.engine import Crawler
from domains.crawler.models import CrawlConfig, FetchResult
from domains.crawler.ports import Queue
from domains.crawler.robots import NoOpRobotsPolicy
from domains.crawler.stages.fetch_stage import DefaultFetchStage
from domains.crawler.stages.parse_stage import DefaultParseStage
from gateways.http.httpx_fetcher import HttpxFetcher
from gateways.memory.queue import InMemoryQueue
from gateways.parsing.selectolax_extractor import SelectolaxExtractor


def build_crawler(config: CrawlConfig, client: httpx.AsyncClient) -> Crawler:
    """Wire the real gateways + default stages into a Crawler."""
    fetcher = HttpxFetcher(client, max_bytes=config.max_bytes)
    fetch_stage = DefaultFetchStage(fetcher=fetcher, robots=NoOpRobotsPolicy())
    parse_stage = DefaultParseStage(extractor=SelectolaxExtractor(), seed_host=config.seed_host)
    # Annotate the locals so the generic queue type is inferred for `ty`.
    frontier: Queue[str] = InMemoryQueue()
    results: Queue[FetchResult] = InMemoryQueue()
    return Crawler(
        config=config,
        fetch_stage=fetch_stage,
        parse_stage=parse_stage,
        frontier=frontier,
        results=results,
    )
