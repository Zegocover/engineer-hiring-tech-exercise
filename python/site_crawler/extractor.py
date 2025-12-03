from __future__ import annotations

import logging
from typing import Set
from urllib.parse import urlparse, urldefrag, urlunparse, urljoin

from bs4 import BeautifulSoup


def get_urls_from_html(html: str, base_url: str) -> Set[str]:
    """Extracts and returns a set of normalized absolute URLs found in HTML.

    - Resolves relative URLs against `base_url`.
    - Removes fragments.
    - Only returns http/https URLs.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        raw_links = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href")
            if href is None:
                continue
            # resolve relative URLs against base_url
            abs_href = urljoin(base_url, href)
            raw_links.add(abs_href)
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
