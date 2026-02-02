"""HTML parsing and link extraction."""

from bs4 import BeautifulSoup

from .url_utils import normalize_url, should_skip_url


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract all valid links from HTML content.

    Parses HTML and extracts href attributes from anchor tags,
    resolving relative URLs and filtering out non-crawlable links.

    Args:
        html: The HTML content to parse.
        base_url: The URL of the page (for resolving relative links).

    Returns:
        List of normalized, absolute URLs found in the HTML.
        Duplicates within the same page are removed.

    Example:
        >>> html = '<a href="/about">About</a><a href="https://example.com">Home</a>'
        >>> extract_links(html, "https://example.com/page")
        ['https://example.com/about', 'https://example.com']
    """
    soup = BeautifulSoup(html, "lxml")

    seen: set[str] = set()
    links: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href_attr = anchor.get("href")

        # Handle BeautifulSoup's return type (can be str, list, or None)
        if isinstance(href_attr, list):
            href = href_attr[0] if href_attr else ""
        else:
            href = href_attr or ""

        # Skip empty hrefs
        if not href or not href.strip():
            continue

        href = href.strip()

        # Skip non-crawlable URLs before normalization
        if should_skip_url(href):
            continue

        # Normalize and resolve relative URLs
        normalized = normalize_url(href, base_url)

        # Skip if we've already seen this URL on this page
        if normalized in seen:
            continue

        # Final validation - must be http/https after normalization
        if not normalized.startswith(("http://", "https://")):
            continue

        seen.add(normalized)
        links.append(normalized)

    return links


def is_html_content_type(content_type: str | None) -> bool:
    """Check if a Content-Type header indicates HTML content.

    Args:
        content_type: The Content-Type header value.

    Returns:
        True if the content type indicates HTML.

    Example:
        >>> is_html_content_type("text/html; charset=utf-8")
        True
        >>> is_html_content_type("application/json")
        False
    """
    if not content_type:
        return False

    # Content-Type may include charset, e.g., "text/html; charset=utf-8"
    content_type_lower = content_type.lower()
    return "text/html" in content_type_lower or "application/xhtml" in content_type_lower
