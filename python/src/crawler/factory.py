"""Composition root wiring: assemble a Crawler from config + an httpx client."""

import httpx

from domains.crawler.engine import Crawler
from domains.crawler.models import CrawlConfig, FetchResult
from domains.crawler.ports import Queue
from gateways.http.httpx_fetcher import HttpxFetcher
from gateways.memory.queue import InMemoryQueue


def crawler_factory(config: CrawlConfig, client: httpx.AsyncClient) -> Crawler:
    """Wire the real fetcher gateway + in-memory queues into a Crawler.

    The engine builds its own parse stage; the composition root only supplies the
    genuinely external collaborators (the HTTP fetcher and the queues).
    """
    # This could be done with a DI framework, but we're keeping it simple here.
    fetcher = HttpxFetcher(client, max_bytes=config.max_bytes)
    # Annotate the locals so the generic queue type is inferred for `ty`.
    frontier: Queue[str] = InMemoryQueue()
    results: Queue[FetchResult] = InMemoryQueue()
    return Crawler(
        config=config,
        fetcher=fetcher,
        frontier=frontier,
        results=results,
    )
