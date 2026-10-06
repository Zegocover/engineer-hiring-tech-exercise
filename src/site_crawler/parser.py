"""Extract links from an HTML document."""

from bs4 import BeautifulSoup

from site_crawler.url_utils import canonical_url


def extract_links(html, page_url):
    """Return absolute http(s) links in document order, including off-site ones.

    ``mailto:``, ``javascript:`` and empty hrefs are skipped. The caller
    decides which of these links are eligible to crawl.
    """
    soup = BeautifulSoup(html, "html.parser")
    links = []
    seen = set()
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        absolute = canonical_url(href, page_url)
        if absolute and absolute not in seen:
            seen.add(absolute)
            links.append(absolute)
    return links
