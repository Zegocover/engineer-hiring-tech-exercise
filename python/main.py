import requests
import sys
import urllib.parse

from bs4 import BeautifulSoup


def get_domain(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.split(":")[0], urllib.parse.urlparse(url).scheme


visited_urls = set()


def crawl_website(url: str, domain: str, scheme: str):
    if not url.startswith("https://") and not url.startswith("http://"):
        url = "http://" + url


    if url in visited_urls:
        return

    visited_urls.add(url)

    # make the request
    response = requests.get(url)

    # parse the response
    soup = BeautifulSoup(response.text, "html.parser")

    # find all the links
    links = soup.find_all("a")

    # print the links
    for link in links:
        if link.get("href") is None:
            continue
        if link.get("href").startswith("/"):
            link = scheme + "://" + domain + link.get("href")
            print(link)
        else:
            print(link.get('href'))



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python main.py <url>")
        sys.exit(1)


    url = sys.argv[1]

    # validate the url and get the domain
    domain, scheme = get_domain(url)

    print(f"domain: {domain}")
    print(f"scheme: {scheme}")
    crawl_website(url, domain, scheme)