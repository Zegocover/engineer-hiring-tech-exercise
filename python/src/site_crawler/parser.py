from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup


def extract_links(html: str, page_url: str) -> tuple[str, ...]:
    """Extract unique, absolute HTTP(S) links from an HTML document."""
    soup = BeautifulSoup(html, "html.parser")
    links: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")
        if isinstance(href, str):
            absolute_url = urljoin(page_url, href)
            without_fragment, _ = urldefrag(absolute_url)
            if without_fragment.startswith(("http://", "https://")):
                parsed_url = urlsplit(without_fragment)
                if not parsed_url.path:
                    without_fragment = urlunsplit(
                        parsed_url._replace(path="/")
                    )
                links.add(without_fragment)

    return tuple(sorted(links))


def extract_links_from_url(url: str) -> list[str]:
    """Fetch a page and return the absolute HTTP(S) links it contains."""
    response = httpx.get(url)
    response.raise_for_status()
    return list(extract_links(response.text, url))
