"""Crawl orchestration: robots, seeding, worker lifecycle, and client ownership."""

from __future__ import annotations

import asyncio

import httpx

from crawler.config import Config
from crawler.web import urls
from crawler.web.fetch import fetch_robots

from .frontier import Frontier
from .outcome import Failed, Outcome, Reporter
from .politeness import Politeness
from .worker import process_url, worker


async def _run(
    base_url: str, client: httpx.AsyncClient, config: Config, report: Reporter
) -> Outcome:
    """Crawl from ``base_url`` and return the base URL's outcome (for exit mapping)."""
    text = await fetch_robots(client, urls.robots_url(base_url))
    politeness = Politeness.from_robots(text, config.user_agent)

    if not politeness.allowed(base_url):
        outcome: Outcome = Failed(base_url, "disallowed by robots.txt")
        report(outcome)
        return outcome

    frontier = Frontier(base_url, politeness)

    queue: asyncio.Queue[str] = asyncio.Queue()
    base_outcome = await process_url(client, base_url, queue, frontier, report)

    if not queue.empty():
        async with asyncio.TaskGroup() as group:
            workers = [
                group.create_task(worker(queue, client, frontier, report))
                for _ in range(config.workers)
            ]
            await queue.join()
            for task in workers:
                task.cancel()
    return base_outcome


async def crawl(base_url: str, config: Config, report: Reporter) -> Outcome:
    """Validate the base URL, own an HTTPX client with the transport policy, and run one crawl."""
    if not urls.is_absolute_http(base_url):
        raise urls.InvalidBaseURLError(f"{base_url}: not an absolute http(s) URL")
    limits = httpx.Limits(max_connections=config.workers, max_keepalive_connections=config.workers)
    async with httpx.AsyncClient(
        follow_redirects=False,
        limits=limits,
        timeout=httpx.Timeout(config.timeout),
        headers={"user-agent": config.user_agent},
    ) as client:
        return await _run(base_url, client, config, report)
