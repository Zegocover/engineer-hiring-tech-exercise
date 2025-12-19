import logging
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Set

from crawler.fetcher import fetch_url
from crawler.parser import extract_links
from crawler.url_utils import normalize_url, get_domain

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Crawler:
    def __init__(
        self,
        start_url: str,
        max_pages: int = 500,
        concurrency: int = 5,
        delay: float = 0.5,
    ):
        self.start_url = normalize_url(start_url)
        self.allowed_domain = get_domain(self.start_url)
        self.max_pages = max_pages
        self.concurrency = concurrency
        self.delay = delay

        self.queue = deque([self.start_url])
        self.visited: Set[str] = set()
        self.crawled_count = 0

    def crawl(self):
        logging.info(
            f"Starting crawl of {self.start_url} (domain: {self.allowed_domain})"
        )

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            while self.queue and self.crawled_count < self.max_pages:
                # Prepare batch
                batch = []
                while len(batch) < self.concurrency and self.queue:
                    url = self.queue.popleft()
                    if url in self.visited:
                        continue
                    self.visited.add(url)
                    batch.append(url)
                    self.crawled_count += 1

                if not batch:
                    continue

                # Submit fetches
                future_to_url = {
                    executor.submit(fetch_url, url): url for url in batch
                }

                for future in as_completed(future_to_url):
                    url, html = future.result()
                    if html:
                        links = extract_links(html, url, self.allowed_domain)
                        print(f"\nCrawled: {url}")
                        print(f"Found {len(links)} internal links:")
                        for link in sorted(links):
                            print(f"  → {link}")

                        # Enqueue new links
                        for link in links:
                            if link not in self.visited:
                                self.queue.append(link)
                    time.sleep(self.delay)  # politeness

        logging.info(f"Crawl completed. Visited {self.crawled_count} pages.")
