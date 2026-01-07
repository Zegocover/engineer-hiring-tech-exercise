"""HTML parsing to extract links from pages."""

from bs4 import BeautifulSoup


def extract_links(html: str) -> list[str]:
    """Extract all href values from anchor tags in HTML.

    Args:
        html: The HTML content to parse.

    Returns:
        List of href values found in the HTML.
    """
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if isinstance(href, str) and href.strip():
            links.append(href.strip())
    return links
