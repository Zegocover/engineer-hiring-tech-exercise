import urllib


class URL:
    def __init__(self, url_string: str):
        self.url_string = self.remove_url_fragment(url_string)
        self.url_string = self.strip_last_slash(self.url_string)

    def __eq__(self, other: "URL"):
        """Equality of URLs is defined as string equality of the url strings"""
        return self.url_string == other.url_string

    def __hash__(self):
        return hash(self.url_string)

    def __str__(self):
        return self.url_string

    def get_domain(self):
        """
        Returns the domain of the URL with the protocol/scheme
        e.g. 'https://example.com/a/path/html' -> 'https://example.com'
        """
        parsed = urllib.parse.urlparse(self.url_string)
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def strip_last_slash(url_str: str) -> str:
        """
        Strips the last slash from a URL

        e.g. 'https://example.com/a/path/' -> 'https://example.com/a/path'
        Args:
            url_str: url to strip

        Returns:
            url string without last slash
        """
        if url_str.endswith("/"):
            return url_str[:-1]
        else:
            return url_str

    @staticmethod
    def remove_url_fragment(url_str: str) -> str:
        """
        Removes fragments from a URL string.
        Fragments are the content that comes after a # in a URL,
        they point to specific anchors within the page.

        e.g. 'https://example.com/page.html#aboutus' -> 'https://example.com/page.html'
        Args:
            url_str: the url to remove fragments from

        Returns:
            url string without fragments
        """
        if "#" in url_str:
            return url_str[: url_str.index("#")]
        else:
            return url_str

    def make_absolute(self, parent_url: "URL"):
        """
        Makes a url absolute whether it's currently absolute or not.
        Will ignore parent_url's domain if the url already has a domain element.

        e.g.
        URL('./page.html').make_absolute('https://a.com')
         -> 'https://a.com/page.html'

        URL('https://a.com/page.html').make_absolute('https://a.com')
         -> 'https://a.com/page.html'

        URL('https://a.com/page.html').make_absolute('https://b.com')
         -> 'https://a.com/page.html'

        Args:
            parent_url: the URL from which the relative link came

        Returns:

        """
        return URL(urllib.parse.urljoin(parent_url.url_string, self.url_string))

    def is_http(self):
        return urllib.parse.urlparse(self.url_string).scheme in ("http", "https")
