from urllib.parse import urlparse, urljoin, urlunparse
from typing import Set


def get_domain(url: str) -> str:
    """Extract the netloc (domain + port) from a URL."""
    parsed = urlparse(url)
    return parsed.netloc.lower()  # lower for consistent comparison


def normalize_url(url: str) -> str:
    """Normalize URL: remove fragment, trailing slashes (including on root), lowercase scheme/host."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url  # invalid, return as-is

    # Remove fragment
    parsed = parsed._replace(fragment="")

    # Remove ALL trailing slashes, even on root (so https://example.com/ → https://example.com)
    path = parsed.path.rstrip("/")

    # If path is now empty after stripping, set it to '' (not '/')
    if path == "":
        path = ""

    # Rebuild with lowercase scheme and netloc
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower(), path=path
    )
    return urlunparse(normalized)


def is_same_domain(url: str, allowed_domain: str) -> bool:
    """Check if URL belongs to the exact same domain (no subdomains)."""
    return get_domain(url) == allowed_domain


def resolve_links(base_url: str, links: Set[str]) -> Set[str]:
    """Resolve relative links to absolute using urljoin and normalize."""
    resolved = set()
    for link in links:
        absolute = urljoin(base_url, link.strip())
        normalized = normalize_url(absolute)
        if normalized:
            resolved.add(normalized)
    return resolved
