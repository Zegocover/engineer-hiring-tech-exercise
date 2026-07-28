

import asyncio

import httpx

from crawler.config import DEFAULT_MAX_CONCURRENCY
from crawler.crawler import Crawler, CrawlResult


def run_crawler(
    start_url: str,
    timeout: float,
    transport: httpx.BaseTransport | None = None,
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
) -> CrawlResult:
    """Synchronous entry point used by tests: builds a client (optionally
    against an in-process transport) and runs the crawl to completion."""

    async def _run() -> CrawlResult:
        async with httpx.AsyncClient(transport=transport) as client:
            return await Crawler().crawl(
                client, start_url, timeout, max_concurrency
            )

    return asyncio.run(_run())
