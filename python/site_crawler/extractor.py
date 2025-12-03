from __future__ import annotations

import logging
from typing import Set
from urllib.parse import urlparse, urldefrag, urlunparse

from lxml import html as lxml_html


def get_urls_from_html(html: str, base_url: str) -> Set[str]:
    """Extracts and returns a set of normalized absolute URLs found in HTML.

    - Resolves relative URLs against `base_url`.
    - Removes fragments.
    - Only returns http/https URLs.
    """
    try:
        doc = lxml_html.fromstring(html)
        doc.make_links_absolute(base_url)
        raw_links = set(doc.xpath("//a[@href]/@href"))
    except Exception:
        logging.exception("Error parsing HTML for URL extraction")
        return set()

    found: Set[str] = set()
    for raw in raw_links:
        # remove fragment
        url, _ = urldefrag(raw)
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            continue
        path = p.path or "/"
        normalized = urlunparse((p.scheme, p.netloc, path, p.params, p.query, ""))
        found.add(normalized)

    return found
