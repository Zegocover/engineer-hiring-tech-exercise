"""Extract links from HTML."""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from crawler.url import is_http_url

DEFAULT_PARSER = "lxml"


class LinkExtractor:
    """Parses HTML into absolute, de-duplicated links, in document order.

    Links are resolved but intentionally left un-normalized and un-filtered, so
    the "links found on this page" output stays faithful to the markup; the
    crawler owns normalization and same-site scoping.
    """

    def __init__(self, parser: str = DEFAULT_PARSER) -> None:
        self._parser = parser

    def extract(self, page_url: str, html: str) -> tuple[str, ...]:
        soup = BeautifulSoup(html, self._parser)
        resolution_base = self._resolution_base(page_url, soup)

        # Only <a href>: <link>/<area>/<img> point at sub-resources, not pages.
        # dict preserves first-seen order while de-duplicating.
        links: dict[str, None] = {}
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href")
            if not isinstance(href, str):  # pragma: no cover - href is never multi-valued
                continue
            href = href.strip()
            if not href:
                continue
            absolute = urljoin(resolution_base, href)
            if is_http_url(absolute):
                links.setdefault(absolute, None)
        return tuple(links)

    @staticmethod
    def _resolution_base(page_url: str, soup: BeautifulSoup) -> str:
        # A <base href> overrides the page URL for relative links (HTML spec).
        base_tag = soup.find("base", href=True)
        if isinstance(base_tag, Tag):
            href = base_tag.get("href")
            if isinstance(href, str) and href.strip():
                return urljoin(page_url, href.strip())
        return page_url
