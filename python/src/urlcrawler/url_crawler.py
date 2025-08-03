import logging
import threading
import time
from typing import Optional
from urllib.parse import urlparse

from .html_parser import HtmlParser
from .http_downloader import HttpDownloader

_LOG = logging.getLogger(__name__)


class UrlCrawler:
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
        self.error_lock = threading.Lock()
        self.thread_pool: list[UrlCrawlerWorker] = []
        self.stop_event = threading.Event()
        # Injection
        # NOTE: Factories are a more robust pattern, but an overkill in this test
        self.downloader = downloader
        self.parser = parser

    def get_next_url(self) -> Optional[str]:
        with self.lock:
            if self.queue:
                url = self.queue.pop(0)
                self.visited.add(url)
                return url
            else:
                return None

    def add_url_if_needed(self, url: str):
        with self.lock:
            if url not in self.visited and url not in self.queue:
                _LOG.debug(f"Adding to queue: {url}")
                self.queue.append(url)
            else:
                _LOG.debug(f"Already visited or in queue: {url}")

    def add_error(self, url: str, ex: Exception):
        with self.error_lock:
            self.errors.append((url, ex))

    def start(self):
        _LOG.info(f"Starting {self.thread_count} worker threads.")
        self.queue.append(self.main_url)
        for i in range(self.thread_count):
            queue_wait_timeout = 10 if self.thread_count > 1 else 0
            worker = UrlCrawlerWorker(self, i, queue_wait_timeout)
            self.thread_pool.append(worker)
            worker.start()
        # Keep main thread awake to listen for exit signals
        try:
            while not self.stop_event.is_set() and any(
                t.is_alive() for t in self.thread_pool
            ):
                # Waiting for stop signal
                time.sleep(0.1)
        finally:
            for t in self.thread_pool:
                t.join()
            self.thread_pool = []

    def stop(self):
        _LOG.info("Stopping")
        self.stop_event.set()


class UrlCrawlerWorker(threading.Thread):
    def __init__(self, crawler: UrlCrawler, worker_id: int, timeout: int = 10):
        super().__init__()
        self.crawler = crawler
        self.worker_id = worker_id
        self.get_url_timeout = timeout

    def run(self):
        _LOG.info(f"Thread({self.worker_id}): Starting")
        while not self.crawler.stop_event.is_set():
            url = self.__get_url_with_timeout()
            if not url:
                _LOG.info(f"Thread({self.worker_id}): No more work")
                break
            # NOTE: Per requirements, print the current URL
            print(url)
            response = self.__get_response(url)
            if not response:
                _LOG.warning(f"Thread({self.worker_id}): No response, skipping {url}")
                continue
            all_urls = []
            try:
                all_urls = self.crawler.parser.find_urls(
                    self.crawler.main_url, response
                )
            except Exception as ex:
                _LOG.error(
                    f"Thread({self.worker_id}): Error parsing response for {url}: {ex}"
                )
                self.crawler.add_error(url, ex)
                continue
            # NOTE: Per requirements, print all the URLs on that page
            # regardless of the visited or enqueued status
            for new_url in all_urls:
                print(f"- {new_url}")
            same_domain_urls = [url for url in all_urls if self.__is_same_domain(url)]
            for new_url in same_domain_urls:
                self.crawler.add_url_if_needed(new_url)
        _LOG.info(f"Thread({self.worker_id}): Stopped")

    def __get_url_with_timeout(self) -> Optional[str]:
        """Retrieve an url from the queue.
        If the queue is empty it waits for timeout until it returns None.
        NOTE: The timeout is needed to wait for other producer threads to generate information.
        Returns:
            Optional[str]: The next URL to process
        """
        _LOG.info(
            f"Thread({self.worker_id}): Visited: {len(self.crawler.visited)}, Queued: {len(self.crawler.queue)} Errors: {len(self.crawler.errors)}"
        )
        if self.get_url_timeout == 0:
            return self.crawler.get_next_url()
        # Wait for a URL to be available in the queue until timeout
        end_time = time.time() + self.get_url_timeout
        while not self.crawler.stop_event.is_set() and time.time() <= end_time:
            url = self.crawler.get_next_url()
            if url:
                return url
        return None

    def __get_response(self, url: str) -> Optional[str]:
        try:
            return self.crawler.downloader.get(url)
        except Exception as ex:
            _LOG.error(f"Thread({self.worker_id}): Error fetching {url}: {ex}")
            self.crawler.add_error(url, ex)
            return None

    def __is_same_domain(self, url: str) -> bool:
        return self.crawler.main_domain == urlparse(url).netloc.lower().replace(
            "www.", ""
        )
