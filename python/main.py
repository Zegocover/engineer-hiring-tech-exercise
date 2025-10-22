import sys
import urllib.parse

from bs4 import BeautifulSoup

from config import Config


def validate_url_domain(url: str) -> bool:
    config = Config()
    url_domain = urllib.parse.urlparse(url).netloc.split(":")[0]
    if url_domain != config.domain:
        return False
    return True

def crawl_website(url: str):
    config = Config()
    visited_urls = config.visited_urls

    # add the scheme if it's not present
    if not url.startswith("https://") and not url.startswith("http://"):
        url = "http://" + url

    if url in visited_urls:
        return

    visited_urls.add(url)

    # make the request
    response = config.session.get(url)

    # parse the response
    soup = BeautifulSoup(response.text, "html.parser")

    # print the links
    for link in soup.find_all("a"):
        href = link.get("href")
        if href is None or href.startswith("#"):
            continue
        if href.startswith("/"):
            href = config.scheme + "://" + config.domain + href
        if href in visited_urls:
            continue
        print(href)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python main.py <url>")
        sys.exit(1)

    config = Config()
    url = sys.argv[1]

    # validate the url and get the domain
    domain, scheme = config.get_domain(url)

    crawl_website(url)