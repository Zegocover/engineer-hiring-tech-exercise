"""The backend's own crawler components.

Every crawl is given these explicitly; the service never relies on the
library's fallback components.
"""

from __future__ import annotations

import httpx
from site_crawler import DefaultHttpxFetcher
from site_crawler.models import FetchResult, PageResult

from crawler_api.jobs import CrawlJob


class SharedClientFetcher:
    """Fetches through the application's shared ``httpx.AsyncClient``.

    Retries, body capping and error mapping come from the library's default
    fetcher. ``aclose`` does nothing: the crawler closes its fetcher when the
    crawl ends, but the client belongs to the application and serves every
    other crawl too.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._inner = DefaultHttpxFetcher(client=client)

    async def fetch(self, url: str) -> FetchResult:
        return await self._inner.fetch(url)

    async def aclose(self) -> None:
        pass


class JobWriter:
    """Records each page on its job and indexes the distinct links found."""

    def __init__(self, job: CrawlJob) -> None:
        self._job = job

    async def write(self, result: PageResult) -> None:
        job = self._job
        job.pages.append(result)
        for link in result.links:
            if link not in job.link_set:
                job.link_set.add(link)
                job.links.append(link)

    async def aclose(self) -> None:
        pass
