import unittest
from urlcrawler.url_crawler import UrlCrawler


class DummyDownloader:
    def get(self, url):
        return "<html><a href='http://test.com/page2.html'>Next</a></html>"


class DummyParser:
    def find_urls(self, base_url, html):
        return ["http://test.com/page2.html"]


class TestUrlCrawler(unittest.TestCase):
    """Unit tests for the UrlCrawler class.
    NOTE: Start is not tested here, as it's are better tested in the integration tests.
    """

    def setUp(self):
        self.downloader = DummyDownloader()
        self.parser = DummyParser()
        self.url = "http://test.com/index.html"
        self.crawler = UrlCrawler(self.url, 1, self.downloader, self.parser)

    def test_add_url_if_needed(self):
        self.crawler.add_url_if_needed("http://test.com/page2.html")
        assert "http://test.com/page2.html" in self.crawler.queue

    def test_add_url_if_needed_does_not_add_if_already_in_queue(self):
        self.crawler.queue.append("http://test.com/page2.html")
        self.crawler.add_url_if_needed("http://test.com/page2.html")
        assert "http://test.com/page2.html" in self.crawler.queue
        assert 1 == len(self.crawler.queue)
        assert 0 == len(self.crawler.visited)

    def test_add_url_if_needed_does_not_add_if_already_in_visited(self):
        self.crawler.visited.add("http://test.com/page2.html")
        self.crawler.add_url_if_needed("http://test.com/page2.html")
        assert "http://test.com/page2.html" not in self.crawler.queue
        assert 0 == len(self.crawler.queue)
        assert 1 == len(self.crawler.visited)

    def test_get_next_url(self):
        self.crawler.queue.append("http://test.com/page2.html")
        url = self.crawler.get_next_url()
        assert url == "http://test.com/page2.html"
        assert url in self.crawler.visited

    def test_add_error(self):
        self.crawler.add_error("http://test.com/bad", Exception("fail"))
        assert 1 == len(self.crawler.errors)
        assert self.crawler.errors[0][0] == "http://test.com/bad"
