"""URL utilities for normalization, validation, and filtering."""

from urllib.parse import urljoin, urlparse, urlunparse

# File extensions to skip (binary/non-HTML content)
SKIP_EXTENSIONS: set[str] = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
    ".mp3", ".mp4", ".avi", ".mov", ".wmv",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".dmg", ".iso",
}

# URL schemes that should not be crawled
SKIP_SCHEMES: set[str] = {
    "mailto", "tel", "javascript", "data", "ftp", "file",
}


def extract_domain(url: str) -> str:
    """Extract the domain (netloc) from a URL.

    Args:
        url: The URL to extract domain from.

    Returns:
        The domain/netloc portion of the URL, lowercased.

    Example:
        >>> extract_domain("https://Example.COM/path")
        'example.com'
    """
    parsed = urlparse(url)
    return parsed.netloc.lower()


def normalize_url(url: str, base_url: str | None = None) -> str:
    """Normalize a URL for consistent deduplication.

    Normalization steps:
    - Resolve relative URLs against base_url if provided
    - Lowercase the scheme and host
    - Remove fragment identifiers (#section)
    - Remove trailing slash (except for root path)

    Args:
        url: The URL to normalize.
        base_url: Optional base URL for resolving relative URLs.

    Returns:
        The normalized URL string.

    Example:
        >>> normalize_url("/about", "https://example.com/page")
        'https://example.com/about'
        >>> normalize_url("https://Example.COM/path/#section")
        'https://example.com/path'
    """
    # Resolve relative URL if base provided
    if base_url:
        url = urljoin(base_url, url)

    parsed = urlparse(url)

    # Lowercase scheme and netloc
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Remove fragment
    fragment = ""

    # Normalize path
    path = parsed.path
    # Empty path should be "/"
    if not path:
        path = "/"
    # Remove trailing slash except for root
    elif path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # Reconstruct URL
    normalized = urlunparse((
        scheme,
        netloc,
        path,
        parsed.params,
        parsed.query,
        fragment,
    ))

    return normalized


def is_same_domain(url: str, base_domain: str) -> bool:
    """Check if a URL belongs to the exact same domain.

    This performs a strict match - subdomains are NOT considered
    the same domain (e.g., www.example.com != example.com).

    Args:
        url: The URL to check.
        base_domain: The target domain to match against.

    Returns:
        True if the URL's domain exactly matches base_domain.

    Example:
        >>> is_same_domain("https://example.com/page", "example.com")
        True
        >>> is_same_domain("https://www.example.com/page", "example.com")
        False
    """
    url_domain = extract_domain(url)
    return url_domain == base_domain.lower()


def should_skip_url(url: str) -> bool:
    """Determine if a URL should be skipped (not crawled).

    Skip conditions:
    - Non-HTTP(S) schemes (mailto:, javascript:, etc.)
    - Binary file extensions (.pdf, .jpg, etc.)
    - Empty or whitespace-only URLs

    Args:
        url: The URL to check.

    Returns:
        True if the URL should be skipped, False otherwise.

    Example:
        >>> should_skip_url("mailto:test@example.com")
        True
        >>> should_skip_url("https://example.com/doc.pdf")
        True
        >>> should_skip_url("https://example.com/page")
        False
    """
    # Skip empty URLs
    if not url or not url.strip():
        return True

    parsed = urlparse(url)

    # Skip non-HTTP schemes
    if parsed.scheme and parsed.scheme.lower() in SKIP_SCHEMES:
        return True

    # Skip binary file extensions
    path_lower = parsed.path.lower()
    for ext in SKIP_EXTENSIONS:
        if path_lower.endswith(ext):
            return True

    return False


def is_valid_http_url(url: str) -> bool:
    """Check if a URL is a valid HTTP/HTTPS URL.

    Args:
        url: The URL to validate.

    Returns:
        True if the URL has http or https scheme and a netloc.

    Example:
        >>> is_valid_http_url("https://example.com")
        True
        >>> is_valid_http_url("/relative/path")
        False
    """
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)
