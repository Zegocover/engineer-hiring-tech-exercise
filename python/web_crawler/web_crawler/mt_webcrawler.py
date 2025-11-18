import multiprocessing
from queue import Queue
from threading import Thread
from time import sleep

import requests
from bs4 import BeautifulSoup
from requests import HTTPError
from web_crawler.url import URL


class MPWebCrawler:
    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth
        self.domain = None
        self.q = Queue()

        # We maintain a collection of links (dict keys)
        # we have visited and their depth (dict values)
        self.visited_links = {}

    def _set_domain(self, url: URL):
        self.domain = url.get_domain()

    # TODO retries
    def get_data(self, url: URL):
        try:
            r = requests.get(url.url_string)
            r.raise_for_status()
        except HTTPError as e:
            print(f"WARNING: {e}")
            return ""

        with open(
            f"/tmp/local_data/{url.url_string.replace('/', '.')}.html", "wb"
        ) as f:
            f.write(r.content)

        return r.content

    def get_data_local(self, url: URL):
        try:
            with open(
                f"/tmp/local_data/{url.url_string.replace('/', '.')}.html", "rb"
            ) as f:
                return f.read()

        except IOError:
            return self.get_data(url)

    def get_links(self, page_content: str):
        """
        Uses BeautifulSoup to find all hyperlinks tagged as <a> with a href.
        """
        soup = BeautifulSoup(page_content, "html.parser")
        links = soup.find_all("a")
        links = [link["href"] for link in links if link.has_attr("href")]

        return links

    def get_all_valid_links(self, url: URL):
        content = self.get_data_local(url)
        links = self.get_links(content)
        links = [URL(link) for link in links]
        links = [link.make_absolute(url) for link in links]
        links = [link for link in links if link.get_domain() == self.domain]

        # Drop trivial links back to self
        if url in links:
            links.remove(url)

        return list(set(links))

    def work_queue(self, q: Queue):
        while True:
            url, depth = self.q.get(block=True)

            self.visited_links[
                url
            ] = depth  # TODO check this is maintained across threads?

            links = self.get_all_valid_links(url)
            output = str(f"{url} contains {len(links)} links")
            for link in links:
                output += f"\n* {link}"

            output += "\n"
            print(output)
            if depth < self.max_depth:
                for link in links:
                    if link not in self.visited_links.keys():
                        self.q.put((link, depth + 1))

    def crawl(self, url: URL, n_threads: int | None = None):
        if n_threads is None:
            n_threads = multiprocessing.cpu_count()

        self._set_domain(url)
        self.q.put((url, 0))

        threads = []
        for i in range(0, n_threads):
            thread = Thread(target=self.work_queue, args=(self.q,))
            thread.start()
            threads.append(thread)

        while True:
            sleep(1)

        # TODO
        # As this code stands, the processes won't finish. We need a way to
        # detect every worker is finished before allowing any to finish.
        # We can't rely on the queue being empty because another worker may add to it.


if __name__ == "__main__":
    wc = MPWebCrawler(max_depth=3)
    wc.crawl(URL("https://bac.org.uk/"))
