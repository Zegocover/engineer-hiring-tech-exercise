import logging
import threading
from typing import Optional
from urllib.parse import urlparse

from .html_parser import HtmlParser
from .http_downloader import HttpDownloader

_LOG = logging.getLogger(__name__)


class URLCrawler:
    def __init__(
        self,
        url: str,
        thread_count: int,
        downloader: HttpDownloader,
        parser: HtmlParser,
    ):
        self.main_url = url
        self.main_domain = urlparse(url).netloc.lower().replace("www.", "")
        # Shared Memory
        self.queue = []
        self.visited = set()
        self.errors: list[tuple[str, Exception]] = []
        # Concurrency
        self.thread_count = thread_count
        self.lock = threading.Lock()
        # Injection
        # NOTE: Factories are a more robust pattern, but an overkill in this test
        self.downloader = downloader
        self.parser = parser

    def start(self):
        self.queue.append(self.main_url)
        while self.queue:
            current_url = self.queue.pop(0)
            _LOG.info(
                f"Visited: {len(self.visited)}, Queued: {len(self.queue)} Errors: {len(self.errors)}, URL: {current_url}"
            )
            # NOTE: Per requirements, print the current URL
            print(current_url)
            self.visited.add(current_url)
            response = self.__get_response(current_url)
            if not response:
                _LOG.warning(f"No response, skipping {current_url}")
                continue
            all_urls = []
            try:
                all_urls = self.parser.find_urls(self.main_url, response)
            except Exception as e:
                _LOG.error(f"Error parsing response for {current_url}: {e}")
                self.errors.append((current_url, e))
                continue
            # NOTE: Per requirements, print all the URLs on that page
            # Regardless of the visited or enqueued status
            print(*all_urls, sep="\n")
            new_valid_urls_to_crawl = [
                url
                for url in all_urls
                if self.__is_same_domain(url)
                and url not in self.visited
                and url not in self.queue
            ]
            self.queue.extend(new_valid_urls_to_crawl)

    def __get_response(self, url: str) -> Optional[str]:
        try:
            return self.downloader.get(url)
        except Exception as e:
            _LOG.error(f"Error fetching {url}: {e}")
            self.errors.append((url, e))
            return None

    def __is_same_domain(self, url: str) -> bool:
        return self.main_domain == urlparse(url).netloc.lower().replace("www.", "")
