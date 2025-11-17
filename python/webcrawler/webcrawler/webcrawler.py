import urllib

from bs4 import BeautifulSoup
import requests
from requests import HTTPError


class URL:
    def __init__(self, url_string: str):
        self.url_string = self.strip_last_slash(url_string)

    def __eq__(self, other: "URL"):
        return self.url_string == other.url_string

    def __hash__(self):
        return hash(self.url_string)

    def __str__(self):
        return self.url_string

    def get_domain(self):
        parsed = urllib.parse.urlparse(self.url_string)
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def strip_last_slash(url_str: str):
        if url_str.endswith("/"):
            return url_str[:-1]
        else:
            return url_str

    # def is_relative(self):
    #     return urllib.parse.urlparse(self.url_string).netloc == ''

    def make_absolute(self, domain: str):
        return URL(urllib.parse.urljoin(domain, self.url_string))

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
        def get_data(self, url: URL):
            try:
                r = requests.get(url.url_string)
                r.raise_for_status()
            except HTTPError as e:
                print(f"WARNING: Get {url} failed. Exception: {e}")
                return ""

            with open(f"/tmp/local_data/{url.url_string.replace('/', '.')}.html", "wb") as f:
                f.write(r.content)

            return r.content

        def get_data_local(self, url: URL):
            try:
                with open(f"/tmp/local_data/{url.url_string.replace('/', '.')}.html", "rb") as f:
                    return f.read()

            except:
                return self.get_data(url)

        def get_links(self, page_content: str):
            """
            Uses BeautifulSoup to find all hyperlinks tagged as <a> with a href.
            """
            soup = BeautifulSoup(page_content, "html.parser")
            links = soup.find_all("a")
            links = [URL(l["href"]) for l in links if l.has_attr("href")]

            return links

        def get_all_valid_links(self, url: URL):
            content = self.get_data_local(url)
            links = self.get_links(content)

            links = [url.make_absolute(self.domain) for url in links]
            links = [l for l in links if l.get_domain()==self.domain]

            # Drop trivial links back to self
            if url in links:
                links.remove(url)

            return links

        def _crawl(self, url: str, current_depth: int = 0):
            children = self.get_all_valid_links(url) # TODO print ALL children, not just valid
            print(f"{current_depth}: {url}")
            # print(children)
            # print(current_depth)

            self.visited_links[url] = current_depth

            if current_depth < self.max_depth:
                for child in children:
                    if child not in self.visited_links.keys():
                        self._crawl(child, current_depth + 1)

        def crawl(self, url: str):
            self._set_domain(url)
            self._crawl(url)




if __name__ == "__main__":
    wc = WebCrawler(max_depth=3)
    wc.crawl(URL("https://www.craigslist.org/about/help/?lang=en&cc=gb"))
