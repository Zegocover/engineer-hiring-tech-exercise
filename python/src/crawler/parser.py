"""HTML parsing and link extraction helpers."""

from bs4 import BeautifulSoup


def extract_links(html: str) -> list[str]:
    """Extract raw href values from anchor tags in the HTML."""
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for anchor in soup.find_all("a"):
        href = anchor.get("href")
        if not href:
            continue
        links.append(href)
    return links
