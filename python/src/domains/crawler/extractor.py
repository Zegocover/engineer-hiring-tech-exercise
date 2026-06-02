"""SelectolaxExtractor: pull navigation hrefs from HTML (fast, lenient parsing).

This is a pure, in-process transformation — no network, no filesystem — so it is
domain logic, not a gateway. It is strategy-shaped (a different parser could
replace it) but is used concretely; no port is defined for it until a second
implementation actually exists.

Pulls href from <a>, <area>, and <link>. If the document declares a <base href>,
relative hrefs are resolved against it here (a <base> overrides the page URL, so
the parse stage cannot do this on its own). Page-relative resolution for the
common no-<base> case happens downstream in urls.normalize()."""

from urllib.parse import urljoin

from selectolax.parser import HTMLParser

_HREF_TAGS = ("a", "area", "link")


class SelectolaxExtractor:
    """Extract navigation hrefs from HTML using selectolax."""

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
