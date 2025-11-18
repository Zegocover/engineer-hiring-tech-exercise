import unittest
from http.client import HTTPException
from unittest.mock import MagicMock, patch, mock_open

from requests import HTTPError

from web_crawler.url import URL
from web_crawler.webcrawler import WebCrawler


class TestWebCrawlerGetData(unittest.TestCase):
    @patch("web_crawler.webcrawler.requests.get")
    def test_get_data_success(self, mock_get):
        # Arrange
        wc = WebCrawler()
        url = URL("https://example.com/page")
        mock_response = MagicMock()
        mock_response.content = b"<html><a href='test.html'>test</a></html>"
        mock_get.return_value = mock_response

        # Act
        result = wc.get_data(url)

        # Assert
        mock_get.assert_called_once_with("https://example.com/page")
        mock_response.raise_for_status.assert_called_once()
        self.assertEqual(b"<html><a href='test.html'>test</a></html>", result)

    @patch("web_crawler.webcrawler.requests.get")
    def test_get_data_http_error_returns_empty_string(self, mock_get):
        # Arrange
        wc = WebCrawler()
        url = URL("https://example.com/error")
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        # Act
        result = wc.get_data(url)

        # Assert
        mock_get.assert_called_once_with("https://example.com/error")
        self.assertEqual("", result)


class TestWebCrawlerGetLinks(unittest.TestCase):
    def test_get_links_parses_anchor_hrefs_to_url_objects(self):
        wc = WebCrawler()
        html = """
        <html>
            <body>
                <a href="https://example.com/a">A</a>
                <a href="/b">B</a>
                <a>no href</a>
            </body>
        </html>
        """

        links = wc.get_links(html)

        self.assertEqual(2, len(links))
        self.assertTrue(all(isinstance(l, URL) for l in links))
        self.assertIn(URL("https://example.com/a"), links)
        self.assertIn(URL("/b"), links)


class TestWebCrawlerGetAllValidLinks(unittest.TestCase):
    @patch.object(WebCrawler, "get_links")
    def test_get_all_valid_links_filters_and_normalises(self, mock_get_links):
        wc = WebCrawler()
        base = URL("https://example.com/start")
        wc.domain = "https://example.com"

        # Simulate HTML content and extracted links
        mock_get_links.return_value = [
            URL("./page1"),
            URL("https://example.com/page2"),
            URL("https://other.com/page3"),  # other domain, should be filtered out
            base,  # self link, should be removed
        ]

        result = wc.get_all_valid_links(base)

        # All returned URLs should be unique, absolute, same domain, and not base itself
        self.assertTrue(all(isinstance(u, URL) for u in result))
        self.assertNotIn(base, result)
        for u in result:
            self.assertEqual("https://example.com", u.get_domain())

        expected = {"https://example.com/page1", "https://example.com/page2"}
        self.assertSetEqual(expected, set([u.url_string for u in result]))


class TestWebCrawlerPrintUrl(unittest.TestCase):
    def test_print_url_outputs_expected_format(self):
        wc = WebCrawler()
        url = URL("https://example.com/start")
        links = [URL("https://example.com/a"), URL("https://example.com/b")]

        with patch("builtins.print") as mock_print:
            wc.print_url(url, links)

        # Ensure one print call with correct structure
        mock_print.assert_called_once()
        output = mock_print.call_args[0][0]
        self.assertIn("https://example.com/start contains 2 links", output)
        self.assertIn("* https://example.com/a", output)
        self.assertIn("* https://example.com/b", output)


class TestWebCrawlerCrawlLogic(unittest.TestCase):
    def test_crawl(self):
        wc = WebCrawler(max_depth=2)
        start_url = URL("https://example.com/start")

        # Map of URL -> list of child URLs (all same domain)
        url_graph = {
            start_url: [URL("https://example.com/a"), URL("https://example.com/b")],
            URL("https://example.com/a"): [URL("https://example.com/c")],
            URL("https://example.com/b"): [],
            URL("https://example.com/c"): [],
        }

        def fake_get_all_valid_links(url):
            return url_graph.get(url, [])

        with patch.object(WebCrawler, "get_all_valid_links", side_effect=fake_get_all_valid_links):
            with patch.object(WebCrawler, "print_url"):  # suppress printing
                wc.crawl(start_url)

        # Domain set from starting URL
        self.assertEqual(start_url.get_domain(), wc.domain)

        # Ensure visited_links contain expected URLs with correct depth
        self.assertIn(start_url, wc.visited_links)
        self.assertIn(URL("https://example.com/a"), wc.visited_links)
        self.assertIn(URL("https://example.com/b"), wc.visited_links)

        # max_depth=2 means c should be visited from a with depth 2
        self.assertIn(URL("https://example.com/c"), wc.visited_links)

        self.assertEqual(0, wc.visited_links[start_url])
        self.assertEqual(1, wc.visited_links[URL("https://example.com/a")])
        self.assertEqual(1, wc.visited_links[URL("https://example.com/b")])
        self.assertEqual(2, wc.visited_links[URL("https://example.com/c")])

    def test_crawl_low_depth(self):
        wc = WebCrawler(max_depth=1)
        start_url = URL("https://example.com/start")

        # Map of URL -> list of child URLs (all same domain)
        url_graph = {
            start_url: [URL("https://example.com/a"), URL("https://example.com/b")],
            URL("https://example.com/a"): [URL("https://example.com/c")],
            URL("https://example.com/b"): [],
            URL("https://example.com/c"): [],
        }

        def fake_get_all_valid_links(url):
            return url_graph.get(url, [])

        with patch.object(WebCrawler, "get_all_valid_links", side_effect=fake_get_all_valid_links):
            with patch.object(WebCrawler, "print_url"):  # suppress printing
                wc.crawl(start_url)

        # Domain set from starting URL
        self.assertEqual(start_url.get_domain(), wc.domain)

        # Ensure visited_links contain expected URLs with correct depth
        self.assertIn(start_url, wc.visited_links)
        self.assertIn(URL("https://example.com/a"), wc.visited_links)
        self.assertIn(URL("https://example.com/b"), wc.visited_links)

        self.assertEqual(0, wc.visited_links[start_url])
        self.assertEqual(1, wc.visited_links[URL("https://example.com/a")])
        self.assertEqual(1, wc.visited_links[URL("https://example.com/b")])


    def test_crawl_with_str_url(self):
        wc = WebCrawler(max_depth=2)
        start_url = "https://example.com/start"

        # Map of URL -> list of child URLs (all same domain)
        url_graph = {
            URL(start_url): [URL("https://example.com/a"), URL("https://example.com/b")],
            URL("https://example.com/a"): [URL("https://example.com/c")],
            URL("https://example.com/b"): [],
            URL("https://example.com/c"): [],
        }

        def fake_get_all_valid_links(url):
            return url_graph.get(url, [])

        with patch.object(WebCrawler, "get_all_valid_links", side_effect=fake_get_all_valid_links):
            with patch.object(WebCrawler, "print_url"):  # suppress printing
                wc.crawl(start_url)

        # Domain set from starting URL
        self.assertEqual("https://example.com", wc.domain)

        # Ensure visited_links contain expected URLs with correct depth
        self.assertIn(URL(start_url), wc.visited_links)
        self.assertIn(URL("https://example.com/a"), wc.visited_links)
        self.assertIn(URL("https://example.com/b"), wc.visited_links)

        # max_depth=2 means c should be visited from a with depth 2
        self.assertIn(URL("https://example.com/c"), wc.visited_links)

        self.assertEqual(0, wc.visited_links[URL(start_url)])
        self.assertEqual(1, wc.visited_links[URL("https://example.com/a")])
        self.assertEqual(1, wc.visited_links[URL("https://example.com/b")])
        self.assertEqual(2, wc.visited_links[URL("https://example.com/c")])


if __name__ == "__main__":
    unittest.main()