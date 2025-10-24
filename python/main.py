import sys
import urllib.parse

from bs4 import BeautifulSoup
from queue import Queue
from threading import Thread
from typing import List,Optional

from config import Config


class WebCrawler:
    def __init__(self, config: Config):
        self.config = config

    def consume(self):
        while True:
            url = self.config.queue.get()
            if url is None:
                break
            self.crawl_website(url)


    def crawl_website(self, url: str):
        if url in self.config.visited_urls:
            return

        self.config.visited_urls.add(url)

        response = self.fetch_url(url)
        if response is None:
            return

        links = self.parse_links(response)
        for link in links:
            self.add_to_queue(link)

        self.config.queue.task_done()

    def fetch_url(self, url: str) -> Optional[str]:
        response = self.config.session.get(url, timeout=10)

        if response.status_code != 200:
            if response.status_code == 429 or response.status_code >= 500:
                print("Too many requests or server error - these should be retried")
                return None
            else:
                # these are 4XX errors - most likely 404 or unauthorised - skip over them and head to next link
                return None
        return response.text

    def parse_links(self, response_text: str) -> List[str]:
        soup = BeautifulSoup(response_text, "html.parser")
        links = []
        # print the links
        for link in soup.find_all("a"):
            href = link.get("href")
            if href is None or href.startswith("#"):
                continue
            if href.startswith("/"):
                href = self.config.scheme + "://" + self.config.domain + href
            links.append(href)

            # print the link as per the challenge requirement
            print(href)
        return links

    def add_to_queue(self, url: str):
        if url in self.config.visited_urls or not self.config.validate_url_domain(url):
            return
        self.config.queue.put(url)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python main.py <url>")
        sys.exit(1)

    config = Config()
    url = sys.argv[1]

    # validate the url and get the domain
    config.get_domain(url)
    
    # add the url to the queue
    config.queue.put(url)

    NUM_CONSUMERS = 5

    # start the consumers
    consumers = [Thread(target=WebCrawler(config).consume) for _ in range(NUM_CONSUMERS)]
    for t in consumers:
        t.start()

    config.queue.join()

    # wait for the consumers to finish
    for t in consumers:
        t.join()

    print("Web crawler finished")