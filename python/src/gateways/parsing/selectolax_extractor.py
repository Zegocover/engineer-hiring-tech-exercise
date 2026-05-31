"""LinkExtractor port implemented with selectolax (fast, lenient HTML parsing).

Pulls href from <a>, <area>, and <link>. If the document declares a <base href>,
relative hrefs are resolved against it here (a <base> overrides the page URL, so
the parse stage cannot do this on its own)."""

from urllib.parse import urljoin

from selectolax.parser import HTMLParser

_HREF_TAGS = ("a", "area", "link")


class SelectolaxExtractor:
    """Extract navigation hrefs from HTML using selectolax."""

    def extract(self, html: str, base_url: str) -> list[str]:
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
