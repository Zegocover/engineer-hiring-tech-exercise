"""URL extraction, normalisation, and domain-filtering utilities."""

from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup


def normalise_url(url: str) -> str:
    """Normalise a URL: lowercase scheme/host, strip fragment, collapse trailing slash.

    This ensures that semantically identical URLs are represented consistently
    so the crawler doesn't revisit the same resource under different string forms.
    """
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    normalised = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=path,
        fragment="",
    )
    return urlunparse(normalised)


def get_domain(url: str) -> str:
    """Extract the lowercased network location (host:port) from a URL."""
    return urlparse(url).netloc.lower()


def is_same_domain(url: str, base_domain: str) -> bool:
    """Check if a URL belongs to exactly the same domain (not subdomains)."""
    return get_domain(url) == base_domain


def is_valid_scheme(url: str) -> bool:
    """Return True if the URL uses http or https."""
    return urlparse(url).scheme.lower() in ("http", "https")


def extract_links(html: str, page_url: str, base_domain: str) -> tuple[set[str], set[str]]:
    """Extract all links from HTML content.

    Args:
        html: Raw HTML content of the page.
        page_url: The URL of the page being parsed (for resolving relative links).
        base_domain: The domain to restrict internal link classification to.

    Returns:
        A tuple of (internal_links, all_links) where:
        - internal_links: normalised same-domain URLs suitable for further crawling
        - all_links: all valid absolute URLs found on the page (for reporting)
    """
    soup = BeautifulSoup(html, "lxml")
    internal_links: set[str] = set()
    all_links: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href: str = anchor["href"].strip()

        # Skip non-navigable href values
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue

        # Resolve relative URLs against the page URL
        absolute = urljoin(page_url, href)

        # Only consider http(s) links
        if not is_valid_scheme(absolute):
            continue

        normalised = normalise_url(absolute)
        all_links.add(normalised)

        # Track same-domain links for crawling
        if is_same_domain(normalised, base_domain):
            internal_links.add(normalised)

    return internal_links, all_links
