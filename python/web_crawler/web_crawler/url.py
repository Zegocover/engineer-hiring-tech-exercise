
import urllib


class URL:
    def __init__(self, url_string: str):
        self.url_string = self.remove_url_fragment(url_string)
        self.url_string = self.strip_last_slash(self.url_string)

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
    def strip_last_slash(url_str: str) -> str:
        if url_str.endswith("/"):
            return url_str[:-1]
        else:
            return url_str

    @staticmethod
    def remove_url_fragment(url_str: str) -> str:
        if "#" in url_str:
            return url_str[:url_str.index("#")]
        else:
            return url_str

    def make_absolute(self, domain: str):
        return URL(urllib.parse.urljoin(domain, self.url_string))