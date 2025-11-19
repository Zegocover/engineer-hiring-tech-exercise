import unittest
from io import StringIO
from unittest.mock import patch

from web_crawler.mt_webcrawler import MTWebCrawler
from web_crawler.st_webcrawler import WebCrawler
from web_crawler.url import URL


class TestIntegration(unittest.TestCase):
    """
    Simple integration tests using mocked HTML pages to test
    WebCrawler and URL classes working together.
    """

    def setUp(self):
        """Set up mock HTML pages for testing"""
        self.base_url = "https://example.com"

        # Simple mock site with 5 pages
        self.mock_pages = {
            "https://example.com": """
                <html>
                    <body>
                        <a href="/about">About</a>
                        <a href="/products">Products</a>
                        <a href="https://external.com">External</a>
                    </body>
                </html>
            """,
            "https://example.com/about": """
                <html>
                    <body>
                        <a href="/">Home</a>
                        <a href="/contact">Contact</a>
                        <a href="/about#team">Team Section</a>
                    </body>
                </html>
            """,
            "https://example.com/products": """
                <html>
                    <body>
                        <a href="/">Home</a>
                        <a href="/products/item1">Item 1</a>
                        <a href="/products/item2">Item 2</a>
                    </body>
                </html>
            """,
            "https://example.com/contact": """
                <html>
                    <body>
                        <a href="/">Home</a>
                        <a href="mailto:test@example.com">Email</a>
                    </body>
                </html>
            """,
            "https://example.com/products/item1": """
                <html>
                    <body>
                        <a href="/products">Back to Products</a>
                        <a href="/products/item2">Item 2</a>
                    </body>
                </html>
            """,
            "https://example.com/products/item2": """
                <html>
                    <body>
                        <a href="/products">Back to Products</a>
                        <a href="/products/item1">Item 1</a>
                    </body>
                </html>
            """,
        }

    def mock_get_data(self, url: URL):
        """Mock implementation that returns predefined HTML pages"""
        page_content = self.mock_pages.get(url.url_string, "<html></html>")
        return page_content.encode("utf-8")

    @patch.object(WebCrawler, "get_data")
    @patch("sys.stdout", new_callable=StringIO)
    def test_basic_crawl(self, mock_stdout, mock_get_data):
        """Test basic crawling from home page"""
        mock_get_data.side_effect = self.mock_get_data

        wc = WebCrawler(max_depth=1)
        wc.crawl(URL("https://example.com"))

        # Should visit home and its direct children
        self.assertIn(URL("https://example.com"), wc.visited_links)
        self.assertIn(URL("https://example.com/about"), wc.visited_links)
        self.assertIn(URL("https://example.com/products"), wc.visited_links)

        # Should not visit external links
        self.assertNotIn(URL("https://external.com"), wc.visited_links)

        # Verify depths
        self.assertEqual(0, wc.visited_links[URL("https://example.com")])
        self.assertEqual(1, wc.visited_links[URL("https://example.com/about")])

        # Verify printed output
        output = mock_stdout.getvalue()

        # Check that home page output is present
        self.assertIn("https://example.com contains 2 links", output)
        self.assertIn("* https://example.com/about", output)
        self.assertIn("* https://example.com/products", output)

        # Check that child pages are printed
        self.assertIn("https://example.com/about contains", output)
        self.assertIn("https://example.com/products contains", output)

        # Check that external links are NOT in the output
        self.assertNotIn("external.com", output)

    @patch.object(WebCrawler, "get_data")
    def test_url_normalization(self, mock_get_data):
        """Test that URL normalization works during crawl"""
        mock_get_data.side_effect = self.mock_get_data

        wc = WebCrawler(max_depth=1)

        with patch.object(WebCrawler, "print_url"):
            wc.crawl(URL("https://example.com/about"))

        # Fragment links should not create separate URLs
        # /about#team should normalize to /about
        for url in wc.visited_links.keys():
            self.assertNotIn("#", url.url_string)

        # Should have /about as visited (not /about#team)
        self.assertIn(URL("https://example.com/about"), wc.visited_links)

    @patch.object(WebCrawler, "get_data")
    def test_depth_limiting(self, mock_get_data):
        """Test that max_depth is respected"""
        mock_get_data.side_effect = self.mock_get_data

        wc = WebCrawler(max_depth=1)

        with patch.object(WebCrawler, "print_url"):
            wc.crawl(URL("https://example.com"))

        # At depth 1, should not reach item pages (depth 2)
        self.assertNotIn(URL("https://example.com/products/item1"), wc.visited_links)
        self.assertNotIn(URL("https://example.com/products/item2"), wc.visited_links)

        # But should reach products page
        self.assertIn(URL("https://example.com/products"), wc.visited_links)

    @patch.object(WebCrawler, "get_data")
    def test_deeper_crawl(self, mock_get_data):
        """Test crawling with depth 2 reaches nested pages"""
        mock_get_data.side_effect = self.mock_get_data

        wc = WebCrawler(max_depth=2)

        with patch.object(WebCrawler, "print_url"):
            wc.crawl(URL("https://example.com"))

        # Should reach nested product pages
        self.assertIn(URL("https://example.com/products/item1"), wc.visited_links)
        self.assertIn(URL("https://example.com/products/item2"), wc.visited_links)

        # Verify depths
        self.assertEqual(1, wc.visited_links[URL("https://example.com/products")])
        self.assertEqual(2, wc.visited_links[URL("https://example.com/products/item1")])

    @patch.object(WebCrawler, "get_data")
    def test_no_duplicate_visits(self, mock_get_data):
        """Test that pages are only visited once"""
        call_count = {}

        def counting_mock(url: URL):
            call_count[url.url_string] = call_count.get(url.url_string, 0) + 1
            return self.mock_get_data(url)

        mock_get_data.side_effect = counting_mock

        wc = WebCrawler(max_depth=2)

        with patch.object(WebCrawler, "print_url"):
            wc.crawl(URL("https://example.com"))

        # Each page should be fetched exactly once
        for url, count in call_count.items():
            self.assertEqual(1, count, f"{url} was fetched {count} times")

    @patch.object(WebCrawler, "get_data")
    def test_relative_to_absolute_conversion(self, mock_get_data):
        """Test that relative URLs are converted to absolute"""
        mock_get_data.side_effect = self.mock_get_data

        wc = WebCrawler(max_depth=1)

        with patch.object(WebCrawler, "print_url"):
            wc.crawl(URL("https://example.com"))

        # All visited URLs should be absolute
        for url in wc.visited_links.keys():
            self.assertTrue(url.url_string.startswith("https://"))
            self.assertIn("example.com", url.url_string)

    @patch.object(WebCrawler, "get_data")
    def test_string_url_input(self, mock_get_data):
        """Test that crawler accepts string URLs"""
        mock_get_data.side_effect = self.mock_get_data

        wc = WebCrawler(max_depth=1)

        with patch.object(WebCrawler, "print_url"):
            wc.crawl("https://example.com")  # String instead of URL object

        # Should still work correctly
        self.assertEqual("https://example.com", wc.domain)
        self.assertIn(URL("https://example.com"), wc.visited_links)

    @patch.object(WebCrawler, "get_data")
    def test_cyclic_links_handled(self, mock_get_data):
        """Test that cyclic links don't cause infinite loops"""
        mock_get_data.side_effect = self.mock_get_data

        wc = WebCrawler(max_depth=3)

        with patch.object(WebCrawler, "print_url"):
            # Products and items have cycles
            wc.crawl(URL("https://example.com/products"))

        # Should visit all pages without duplicates
        self.assertIn(URL("https://example.com/products"), wc.visited_links)
        self.assertIn(URL("https://example.com/products/item1"), wc.visited_links)
        self.assertIn(URL("https://example.com/products/item2"), wc.visited_links)

        # Should have reasonable number of visits (no infinite loop)
        self.assertLessEqual(len(wc.visited_links), 10)

    @patch.object(WebCrawler, "get_data")
    def test_domain_filtering(self, mock_get_data):
        """Test that only same-domain links are followed"""
        mock_get_data.side_effect = self.mock_get_data

        wc = WebCrawler(max_depth=2)

        with patch.object(WebCrawler, "print_url"):
            wc.crawl(URL("https://example.com"))

        # All visited URLs should be from example.com
        for url in wc.visited_links.keys():
            self.assertEqual("https://example.com", url.get_domain())


if __name__ == "__main__":
    unittest.main()
