import sys
import urllib.parse

from bs4 import BeautifulSoup
from typing import Optional

from config import Config


def validate_url_domain(url: str) -> bool:
    config = Config()
    url_domain = urllib.parse.urlparse(url).netloc.split(":")[0]
    if url_domain != config.domain:
        return False
    return True

def crawl_website(url: str, timeout: Optional[int] = None):
    config = Config()
    visited_urls = config.visited_urls

    # add the scheme if it's not present
    if not url.startswith("https://") and not url.startswith("http://"):
        url = config.scheme + "://" + url

    if url in visited_urls:
        return

    visited_urls.add(url)

    # make the request
    response = config.session.get(url, timeout=timeout)

    if response.status_code != 200:
        if response.status_code == 429 or response.status_code >= 500:
            print("Too many requests or server error - these should be retried")
            return
        else:
            # these are 4XX errors - most likely 404 or unauthorised - skip over them and head to next link
            return

    # parse the response
    soup = BeautifulSoup(response.text, "html.parser")

    # print the links
    for link in soup.find_all("a"):
        href = link.get("href")
        if href is None or href.startswith("#"):
            continue
        if href.startswith("/"):
            href = config.scheme + "://" + config.domain + href
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