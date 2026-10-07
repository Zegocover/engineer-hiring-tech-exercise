"""The backend's own crawler components.

Every crawl is given these explicitly; the service never relies on the
library's fallback components.
"""

from __future__ import annotations

import codecs
import contextlib
from html.parser import HTMLParser
from urllib.parse import urljoin

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


class StdlibHtmlParser:
    """Finds ``<a href>`` links with Python's built-in :mod:`html.parser`.

    Returns the same links as the library's selectolax-based default: non-blank
    hrefs in document order, joined with the page's first ``<base href>`` (even
    for links that come before it). Pure Python, so slower than selectolax.
    """

    def parse(self, page: FetchResult) -> list[str]:
        collector = _LinkCollector()
        collector.feed(_decode(page))
        collector.close()
        if collector.base_href is None or not collector.base_href.strip():
            return collector.hrefs
        base_url = urljoin(page.final_url, collector.base_href.strip())
        return [urljoin(base_url, href) for href in collector.hrefs]


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.base_href: str | None = None  # from the first <base> that has an href attribute
        self._template_depth = 0  # <template> content is inert in HTML5: not part of the page

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "template":
            self._template_depth += 1
        if self._template_depth or tag not in ("a", "base"):
            return
        href = next((value for name, value in attrs if name == "href"), None)
        if href is None:
            return
        if tag == "base":
            if self.base_href is None:
                self.base_href = href
        elif href.strip():
            self.hrefs.append(href.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag == "template" and self._template_depth:
            self._template_depth -= 1


def _decode(page: FetchResult) -> str:
    """Decode with the Content-Type charset if Python knows it, else UTF-8; never raises."""
    encoding = "utf-8"
    for param in (page.content_type or "").split(";")[1:]:
        name, _, value = param.partition("=")
        if name.strip().lower() == "charset":
            with contextlib.suppress(LookupError):  # unknown charset: keep UTF-8
                encoding = codecs.lookup(value.strip().strip('"')).name
    return page.body.decode(encoding, errors="replace")
