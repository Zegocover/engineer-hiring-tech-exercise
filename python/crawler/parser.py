from bs4 import BeautifulSoup
from typing import Set
from urllib.parse import urlparse
from crawler.url_utils import resolve_links, is_same_domain, normalize_url


def extract_links(html: str, base_url: str, allowed_domain: str) -> Set[str]:
    """
    Extract all <a href> links from HTML, filter to same domain, ignore non-http(s).
    Returns a set of normalized absolute URLs.
    """
    soup = BeautifulSoup(html, "lxml")
    links = set()

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href:
            continue
        if href.startswith("#"):
            continue  # Skip anchor-only links (same page)

        # Skip non-http(s) schemes early
        parsed = urlparse(href)
        if parsed.scheme and parsed.scheme not in ("http", "https"):
            continue

        absolute = (
            href if parsed.scheme else None
        )  # will be resolved in url_utils
        links.add(absolute or href)  # raw href if absolute, else relative

    # Resolve and normalize using url_utils
    resolved = resolve_links(base_url, links)

    # Final filter: only same domain
    return {link for link in resolved if is_same_domain(link, allowed_domain)}
