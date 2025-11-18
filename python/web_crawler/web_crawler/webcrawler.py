from typing import List

import requests
from bs4 import BeautifulSoup
from requests import HTTPError
from web_crawler.url import URL

if __name__ == "__main__":

    class WebCrawler:
        def __init__(self, max_depth: int = 3):
            self.max_depth = max_depth
            self.domain = None

            # We maintain a collection of links (dict keys)
            # we have visited and their depth (dict values)
            self.visited_links = {}

        def _set_domain(self, url: URL):
            self.domain = url.get_domain()

        # TODO retries
        def get_data(self, url: URL) -> str:
            """
            Makes a GET request to the specified URL and returns the content as a string

            Args:
                url: The URL to make a GET request to

            Returns:
                content of the GET request
            """
            try:
                r = requests.get(url.url_string)
                r.raise_for_status()
            except HTTPError as e:
                print(f"WARNING: Get {url} failed. Exception: {e}")
                return ""

            with open(
                f"/tmp/local_data/{url.url_string.replace('/', '.')}.html", "wb"
            ) as f:
                f.write(r.content)

            return r.content

        def get_data_local(self, url: URL):
            """TODO: DELETE"""
            try:
                with open(
                    f"/tmp/local_data/{url.url_string.replace('/', '.')}.html", "rb"
                ) as f:
                    return f.read()

            except IOError:
                return self.get_data(url)

        def get_links(self, page_content: str) -> List[URL]:
            """
            Collects all links from `page_content`

            Args:
                page_content: string of HTML content of page

            Returns:
                list of URL objects
            """
            soup = BeautifulSoup(page_content, "html.parser")
            links = soup.find_all("a")
            links = [URL(link["href"]) for link in links if link.has_attr("href")]

            return links

        def get_all_valid_links(self, url: URL) -> List[URL]:
            """
            Collects all valid links from `url`. Valid means non-trivial links
            within the same domain. It will also force all URLs to be absolute.

            Args:
                url: URL of the page to get links from

            Returns:
                list of distinct URL objects
            """
            content = self.get_data_local(url)
            links = self.get_links(content)

            links = [url.make_absolute(self.domain) for url in links]
            links = [link for link in links if link.get_domain() == self.domain]

            # Drop trivial links back to self
            if url in links:
                links.remove(url)

            return list(set(links))

        @staticmethod
        def print_url(url: URL, links: List[URL]) -> None:
            """
            Pretty prints the URL and all its links
            Args:
                url: URL to be printed
                links: list of links

            Returns:
                None
            """
            output = str(f"{url} contains {len(links)} links")
            for link in links:
                output += f"\n* {link}"

            output += "\n"
            print(output)

        def _crawl(self, url: URL, current_depth: int = 0) -> None:
            """
            Iterates the crawling, finding all links from `url` and
            recursively calling this function on them until max
            depth is achieved

            Args:
                url: URL to be crawled
                current_depth: number of links followed from initial URL

            Returns:
                None
            """
            links = self.get_all_valid_links(url)
            self.print_url(url, links)
            self.visited_links[url] = current_depth

            if current_depth < self.max_depth:
                for link in links:
                    if link not in self.visited_links.keys():
                        self._crawl(link, current_depth + 1)

        def crawl(self, url: URL | str) -> None:
            """
            Initiates a crawling of `url`
            Args:
                url: URL to be crawled as either a URL object or a string

            Returns:
                None
            """
            if isinstance(url, str):
                url = URL(url)

            self._set_domain(url)
            self._crawl(url)


if __name__ == "__main__":
    wc = WebCrawler(max_depth=3)
    wc.crawl(URL("https://www.craigslist.org/about/help/?lang=en&cc=gb"))
