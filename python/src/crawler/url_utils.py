"""URL utilities for the crawler."""

from urllib.parse import urljoin, urlparse, urlunparse


def process_url(href: str, base_url: str, base_domain: str) -> str | None:
    """Process a discovered href into a normalised absolute URL if it's valid and on the same domain.

    Args:
        href: The href value found on a page (may be relative or absolute).
        base_url: The URL of the page where the href was found.
        base_domain: The domain we're crawling (without www prefix).

    Returns:
        Normalised absolute URL if valid and same domain, None otherwise.
    """
    # Resolve relative URLs
    absolute = urljoin(base_url, href)
    parsed = urlparse(absolute)

    # Must be HTTP/HTTPS
    if parsed.scheme not in ("http", "https"):
        return None

    # Check same domain (normalise www)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    if domain != base_domain:
        return None

    # Normalise: lowercase, remove fragment, remove trailing slash (except root), strip www
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/") or "/"
    normalised = urlunparse((
        parsed.scheme.lower(),
        netloc,
        path,
        parsed.params,
        parsed.query,
        "",  # Remove fragment
    ))

    return normalised


def get_base_domain(url: str) -> str:
    """Extract the base domain from a URL, removing www prefix.

    Args:
        url: The starting URL for the crawl.

    Returns:
        The domain without www prefix.
    """
    domain = urlparse(url).netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain
