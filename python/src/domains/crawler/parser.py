"""Link parsing for the crawl domain: HTML in, normalized + classified links out.

Two pure, in-process transforms — no network, no filesystem — so this is domain
logic rather than a gateway. ``SelectolaxExtractor`` pulls raw hrefs out of HTML;
``LinkParser`` normalizes them and splits on-host (enqueue) from off-site
(list-only). Both are strategy-shaped — a different parser could replace them —
but are used concretely, so no port is defined until a second implementation
actually exists."""

from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from domains.crawler.models import FetchResult, PageResult, ParseOutcome
from domains.crawler.urls import normalize, same_host

_HREF_TAGS = ("a", "area", "link")


class SelectolaxExtractor:
    """Extract navigation hrefs from HTML using selectolax (fast, lenient).

    Pulls href from <a>, <area>, and <link>. If the document declares a
    <base href>, relative hrefs are resolved against it here — a <base> overrides
    the page URL, so ``LinkParser`` cannot do this on its own. Page-relative
    resolution for the common no-<base> case happens downstream in
    ``urls.normalize()``.
    """

    def extract(self, html: str) -> list[str]:
        tree = HTMLParser(html)
        base = self._base_href(tree)
        hrefs: list[str] = []
        for tag in _HREF_TAGS:
            for node in tree.css(tag):
                href = node.attributes.get("href")
                if href:
                    hrefs.append(urljoin(base, href) if base else href)
        return hrefs

    @staticmethod
    def _base_href(tree: HTMLParser) -> str | None:
        node = tree.css_first("base[href]")
        if node is None:
            return None
        return node.attributes.get("href") or None


class LinkParser:
    """Turn a FetchResult into a PageResult plus on-host enqueue candidates.

    Owns its HTML extractor directly: extraction is a pure in-domain transform,
    so there is no port to inject.
    """

    def __init__(self, seed_host: str) -> None:
        self._seed_host = seed_host
        self._extractor = SelectolaxExtractor()

    async def parse(self, result: FetchResult) -> ParseOutcome:
        if result.html is None:
            page = PageResult(
                url=result.final_url,
                links=(),
                status=result.status,
                error=result.error,
            )
            return ParseOutcome(page=page, on_host_links=())

        normalized: set[str] = set()
        for href in self._extractor.extract(result.html):
            canonical = normalize(href, result.final_url)
            if canonical is not None:
                normalized.add(canonical)

        all_links = tuple(sorted(normalized))
        on_host = tuple(u for u in all_links if same_host(u, self._seed_host))
        page = PageResult(
            url=result.final_url,
            links=all_links,
            status=result.status,
            error=result.error,
        )
        return ParseOutcome(page=page, on_host_links=on_host)
