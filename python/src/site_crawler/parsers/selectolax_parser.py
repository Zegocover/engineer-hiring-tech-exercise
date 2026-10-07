from __future__ import annotations

from urllib.parse import urljoin

from selectolax.lexbor import LexborHTMLParser

from site_crawler.models import FetchResult


class DefaultSelectolaxParser:
    """Default parser: ``<a href>`` links in document order.

    Uses selectolax's Lexbor backend, a fast HTML5-compliant parser that
    copes with malformed markup. When the page has ``<base href>``, links are
    returned already joined with it, per the :class:`Parser` contract.
    """

    def parse(self, page: FetchResult) -> list[str]:
        tree = LexborHTMLParser(page.body)
        base = tree.css_first("base[href]")
        base_href = (base.attributes.get("href") or "").strip() if base is not None else ""
        base_url = urljoin(page.final_url, base_href) if base_href else None

        links: list[str] = []
        for node in tree.css("a[href]"):
            href = (node.attributes.get("href") or "").strip()
            if not href:
                continue
            links.append(urljoin(base_url, href) if base_url else href)
        return links
