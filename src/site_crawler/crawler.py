"""Async single-host crawler."""

import asyncio
from dataclasses import dataclass, field

from site_crawler.client import HttpClient
from site_crawler.parser import extract_links
from site_crawler.url_utils import canonical_url, hostname_of, same_site


@dataclass
class Page:
    url: str
    links: list = field(default_factory=list)
    error: str = ""


class Crawler:
    """Breadth-first crawl of one host.

    A fixed pool of workers shares one ``HttpClient``. ``--concurrency`` caps
    both workers and pooled connections. Each URL is enqueued once, so a
    cycle (A links to B, B links to A) fetches each page a single time.
    """

    def __init__(self, concurrency=10, timeout=10, max_pages=None, user_agent="site-crawler/0.1"):
        if concurrency < 1:
            raise ValueError("concurrency must be >= 1")
        self.concurrency = concurrency
        self.timeout = timeout
        self.max_pages = max_pages
        self.user_agent = user_agent

    async def crawl(self, start_url):
        root = canonical_url(start_url)
        if root is None:
            raise ValueError("start URL must be an absolute http(s) URL")
        root_host = hostname_of(root)

        queue = asyncio.Queue()
        queue.put_nowait(root)
        seen = {root}
        pages = []
        # A dict so workers can update the count. A bare int assigned inside
        # the nested function would be a new local and the enqueue would throw.
        state = {"scheduled": 1}

        async with HttpClient(self.concurrency, self.timeout, self.user_agent) as client:
            async def worker():
                while True:
                    try:
                        url = await queue.get()
                    except asyncio.CancelledError:
                        break
                    try:
                        page = await self._fetch(client, url, root_host)
                        pages.append(page)
                        if page.error or self._at_cap(state):
                            continue
                        for link in page.links:
                            if link in seen or not same_site(link, root_host):
                                continue
                            if self._at_cap(state):
                                break
                            seen.add(link)
                            state["scheduled"] += 1
                            queue.put_nowait(link)
                    finally:
                        queue.task_done()

            workers = [asyncio.create_task(worker()) for _ in range(self.concurrency)]
            await queue.join()
            for task in workers:
                task.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

        return pages

    def _at_cap(self, state):
        return self.max_pages is not None and state["scheduled"] >= self.max_pages

    async def _fetch(self, client, url, root_host):
        result = await client.fetch(url, root_host)
        if result.error or not result.html:
            return Page(result.final_url or url, error=result.error)
        page_url = result.final_url or url
        return Page(page_url, extract_links(result.html, page_url))


def format_page(page):
    lines = [page.url if not page.error else "%s  (%s)" % (page.url, page.error)]
    for link in page.links:
        lines.append("  %s" % link)
    return "\n".join(lines)
