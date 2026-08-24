"""Single-URL processing and the worker coroutine that runs the crawl loop."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx
from lxml.etree import LxmlError

from crawler.web.dom import extract_anchor_urls
from crawler.web.fetch import FetchError, FetchOk, fetch_html

from .outcome import Failed, NonPage, Outcome, Page, Reporter

if TYPE_CHECKING:
    from .frontier import Frontier


async def process_url(
    client: httpx.AsyncClient,
    url: str,
    queue: asyncio.Queue[str],
    frontier: Frontier,
    report: Reporter,
) -> Outcome:
    """Fetch, extract, schedule discovered links, report, and return the outcome."""
    result = await fetch_html(client, url)
    outcome: Outcome
    match result:
        case FetchOk(body=body):
            try:
                links = extract_anchor_urls(body, url)
            except LxmlError as error:
                outcome = Failed(url, f"parse error: {error}")
            else:
                outcome = Page(url, tuple(links))
        case FetchError(kind="non_html", detail=detail):
            outcome = NonPage(url, f"non-HTML: {detail}")
        case FetchError(kind=kind, detail=detail):
            outcome = Failed(url, f"{kind}: {detail}")

    if isinstance(outcome, Page):
        for discovered in frontier.admit(outcome.links):
            queue.put_nowait(discovered)
    report(outcome)
    return outcome


async def worker(
    queue: asyncio.Queue[str],
    client: httpx.AsyncClient,
    frontier: Frontier,
    report: Reporter,
) -> None:
    """Process items until cancelled; ``task_done`` in ``finally`` keeps ``join()`` live."""
    while True:
        url = await queue.get()
        try:
            await process_url(client, url, queue, frontier, report)
        finally:
            queue.task_done()
