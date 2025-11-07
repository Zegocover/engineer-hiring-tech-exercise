from bs4 import BeautifulSoup
from utils.urls import clean_url


def parse_urls_from_html(html: str)-> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a")
    return _process_links(links)


def _process_links(links: list) -> list[str]:
    urls = set()
    for link in links:
        href = link.get("href")
        if href:
            url  = clean_url(href)
            urls.add(url)
    return list(urls)