import urllib.parse


class FetchUrlFilter:
    def __init__(self, base_url):
        self.base_url_parsed = urllib.parse.urlparse(base_url)
        self.visited_urls = set()

    def should_fetch(self, url):
        parsed_url = urllib.parse.urlparse(url)

        if parsed_url.scheme not in ("http", "https"):
            return False

        if parsed_url.netloc != self.base_url_parsed.netloc:
            return False

        url_without_fragment = urllib.parse.urldefrag(url).url
        if url_without_fragment in self.visited_urls:
            return False

        self.visited_urls.add(url_without_fragment)
        return True
