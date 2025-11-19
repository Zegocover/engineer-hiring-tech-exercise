"""
This is a multithreaded version of the crawler. It's not tested
 and a termination issue is mentioned in the crawl() function.

The single-threaded version is available in st_webcrawler.py
"""
import logging
import multiprocessing
from queue import Queue
from threading import Thread
from typing import List

import requests
from bs4 import BeautifulSoup
from requests import HTTPError
from web_crawler.url import URL
from web_crawler.webcrawler import WebCrawler

logger = logging.getLogger(__name__)


class MTWebCrawler(WebCrawler):
    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth
        self.domain = None
        self.q = Queue()

        # We maintain a collection of links (dict keys)
        # we have visited and their depth (dict values)
        self.visited_links = {}

    def _set_domain(self, url: URL) -> None:
        """Sets the domain of the crawler to stay within"""
        self.domain = url.get_domain()

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
            return r.content
        except HTTPError as e:
            # TODO - we can do much more sophisticated error
            # handling here, e.g. 503s should be retried
            logger.warning(f"Get {url} failed. Exception: {e}")
            return ""

    def get_links(self, page_content: str) -> List[str]:
        """
        Collects all links from `page_content`

        Args:
            page_content: string of HTML content of page

        Returns:
            list of URL objects
        """
        soup = BeautifulSoup(page_content, "html.parser")
        links = soup.find_all("a")
        links = [link["href"] for link in links if link.has_attr("href")]

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
        content = self.get_data(url)
        links = self.get_links(content)
        links = [URL(link) for link in links]
        links = [link.make_absolute(url) for link in links]
        links = [
            link for link in links
            if link.is_http() and link.get_domain() == self.domain
        ]

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

    def _crawl(self, url: URL, depth: int) -> None:
        """
        Iterates the crawling, finding all links from `url` and
        adds uncrawled links to the queue for further crawling

        Args:
            url: URL to be crawled
            current_depth: number of links followed from initial URL

        Returns:
            None
        """
        # Update the map of visited links
        self.visited_links[url] = depth

        # get all links from this URL
        links = self.get_all_valid_links(url)

        # print output
        self.print_url(url, links)

        # If we haven't reached the max depth, queue the links for crawling
        if depth < self.max_depth:
            for link in links:
                if link not in self.visited_links.keys():
                    self.q.put((link, depth + 1))

    def _work_queue(self) -> None:
        """Gets the next item from the queue and crawls it"""
        while True:
            url, depth = self.q.get(block=True)
            self._crawl(url, depth)

    def crawl(self, url: URL, n_threads: int | None = None) -> None:
        """
        Initiates a crawling of `url`
        Args:
            url: URL to be crawled as either a URL object or a string

        Returns:
            None
        """
        if n_threads is None:
            n_threads = multiprocessing.cpu_count()

        self._set_domain(url)
        self.q.put((url, 0))

        threads = []
        for i in range(0, n_threads):
            thread = Thread(target=self._work_queue)
            thread.start()
            threads.append(thread)

        # TODO - As this code stands, the processes won't terminate. We need a way to
        # detect every worker is finished before allowing any to finish.
        # We can't rely on the queue being empty because another worker may add to it.
