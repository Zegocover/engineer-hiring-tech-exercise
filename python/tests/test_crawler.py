"""Integration tests for crawler module."""

import pytest
from aioresponses import aioresponses

from crawler.crawler import Crawler, CrawlerConfig, CrawlResult


class TestCrawler:
    """Tests for Crawler class."""

    @pytest.fixture
    def mock_aioresponse(self):
        """Fixture providing aioresponses context."""
        with aioresponses() as m:
            yield m

    async def test_crawls_single_page(self, mock_aioresponse) -> None:
        """Test crawling a single page with no links."""
        mock_aioresponse.get(
            "https://example.com/",
            body="<html><body><p>No links here</p></body></html>",
            headers={"Content-Type": "text/html"},
        )

        crawler = Crawler("https://example.com")
        results = await crawler.crawl()

        assert len(results) == 1
        assert results[0].url == "https://example.com/"
        assert results[0].links == []
        assert results[0].error is None

    async def test_crawls_page_with_links(self, mock_aioresponse) -> None:
        """Test crawling a page and discovering links."""
        mock_aioresponse.get(
            "https://example.com/",
            body="""
            <html><body>
                <a href="/about">About</a>
                <a href="/contact">Contact</a>
            </body></html>
            """,
            headers={"Content-Type": "text/html"},
        )
        mock_aioresponse.get(
            "https://example.com/about",
            body="<html><body><p>About page</p></body></html>",
            headers={"Content-Type": "text/html"},
        )
        mock_aioresponse.get(
            "https://example.com/contact",
            body="<html><body><p>Contact page</p></body></html>",
            headers={"Content-Type": "text/html"},
        )

        crawler = Crawler("https://example.com")
        results = await crawler.crawl()

        assert len(results) == 3
        urls = {r.url for r in results}
        assert "https://example.com/" in urls
        assert "https://example.com/about" in urls
        assert "https://example.com/contact" in urls

    async def test_filters_external_domains(self, mock_aioresponse) -> None:
        """Test that external domain links are not followed."""
        mock_aioresponse.get(
            "https://example.com/",
            body="""
            <html><body>
                <a href="/internal">Internal</a>
                <a href="https://other.com/external">External</a>
            </body></html>
            """,
            headers={"Content-Type": "text/html"},
        )
        mock_aioresponse.get(
            "https://example.com/internal",
            body="<html><body><p>Internal page</p></body></html>",
            headers={"Content-Type": "text/html"},
        )

        crawler = Crawler("https://example.com")
        results = await crawler.crawl()

        assert len(results) == 2
        urls = {r.url for r in results}
        assert "https://example.com/" in urls
        assert "https://example.com/internal" in urls
        assert "https://other.com/external" not in urls

    async def test_filters_subdomains(self, mock_aioresponse) -> None:
        """Test that subdomain links are not followed."""
        mock_aioresponse.get(
            "https://example.com/",
            body="""
            <html><body>
                <a href="/page">Page</a>
                <a href="https://www.example.com/sub">Subdomain</a>
            </body></html>
            """,
            headers={"Content-Type": "text/html"},
        )
        mock_aioresponse.get(
            "https://example.com/page",
            body="<html><body><p>Page</p></body></html>",
            headers={"Content-Type": "text/html"},
        )

        crawler = Crawler("https://example.com")
        results = await crawler.crawl()

        assert len(results) == 2
        urls = {r.url for r in results}
        assert "https://www.example.com/sub" not in urls

    async def test_avoids_duplicate_crawls(self, mock_aioresponse) -> None:
        """Test that the same URL is not crawled twice."""
        mock_aioresponse.get(
            "https://example.com/",
            body="""
            <html><body>
                <a href="/page">Page</a>
                <a href="/page">Same Page</a>
            </body></html>
            """,
            headers={"Content-Type": "text/html"},
        )
        mock_aioresponse.get(
            "https://example.com/page",
            body='<html><body><a href="/">Back</a></body></html>',
            headers={"Content-Type": "text/html"},
        )

        crawler = Crawler("https://example.com")
        results = await crawler.crawl()

        # Should only crawl each URL once
        assert len(results) == 2
        urls = [r.url for r in results]
        assert urls.count("https://example.com/") == 1
        assert urls.count("https://example.com/page") == 1

    async def test_handles_circular_links(self, mock_aioresponse) -> None:
        """Test handling of circular link references."""
        mock_aioresponse.get(
            "https://example.com/",
            body='<html><body><a href="/page">Page</a></body></html>',
            headers={"Content-Type": "text/html"},
        )
        mock_aioresponse.get(
            "https://example.com/page",
            body='<html><body><a href="/">Home</a></body></html>',
            headers={"Content-Type": "text/html"},
        )

        crawler = Crawler("https://example.com")
        results = await crawler.crawl()

        assert len(results) == 2

    async def test_skips_non_html_content(self, mock_aioresponse) -> None:
        """Test that non-HTML responses are skipped."""
        mock_aioresponse.get(
            "https://example.com/",
            body='<html><body><a href="/data.json">Data</a></body></html>',
            headers={"Content-Type": "text/html"},
        )
        mock_aioresponse.get(
            "https://example.com/data.json",
            body='{"key": "value"}',
            headers={"Content-Type": "application/json"},
        )

        crawler = Crawler("https://example.com")
        results = await crawler.crawl()

        # JSON endpoint should be crawled but return no links
        json_result = next(r for r in results if r.url == "https://example.com/data.json")
        assert json_result.links == []

    async def test_handles_http_errors(self, mock_aioresponse) -> None:
        """Test handling of HTTP error responses."""
        mock_aioresponse.get(
            "https://example.com/",
            body='<html><body><a href="/missing">Missing</a></body></html>',
            headers={"Content-Type": "text/html"},
        )
        mock_aioresponse.get(
            "https://example.com/missing",
            status=404,
            body="Not Found",
            headers={"Content-Type": "text/html"},
        )

        crawler = Crawler("https://example.com")
        results = await crawler.crawl()

        error_result = next(r for r in results if r.url == "https://example.com/missing")
        assert error_result.error == "HTTP 404"

    async def test_respects_max_pages_limit(self, mock_aioresponse) -> None:
        """Test that max_pages configuration is respected."""
        mock_aioresponse.get(
            "https://example.com/",
            body="""
            <html><body>
                <a href="/page1">Page 1</a>
                <a href="/page2">Page 2</a>
                <a href="/page3">Page 3</a>
            </body></html>
            """,
            headers={"Content-Type": "text/html"},
        )
        mock_aioresponse.get(
            "https://example.com/page1",
            body="<html><body><p>Page 1</p></body></html>",
            headers={"Content-Type": "text/html"},
        )
        mock_aioresponse.get(
            "https://example.com/page2",
            body="<html><body><p>Page 2</p></body></html>",
            headers={"Content-Type": "text/html"},
        )
        mock_aioresponse.get(
            "https://example.com/page3",
            body="<html><body><p>Page 3</p></body></html>",
            headers={"Content-Type": "text/html"},
        )

        config = CrawlerConfig(max_pages=2)
        crawler = Crawler("https://example.com", config=config)
        results = await crawler.crawl()

        assert len(results) == 2

    async def test_callback_invoked_per_page(self, mock_aioresponse) -> None:
        """Test that on_page_crawled callback is invoked."""
        mock_aioresponse.get(
            "https://example.com/",
            body='<html><body><a href="/page">Page</a></body></html>',
            headers={"Content-Type": "text/html"},
        )
        mock_aioresponse.get(
            "https://example.com/page",
            body="<html><body><p>Page</p></body></html>",
            headers={"Content-Type": "text/html"},
        )

        callback_results: list[CrawlResult] = []

        def callback(result: CrawlResult) -> None:
            callback_results.append(result)

        crawler = Crawler("https://example.com", on_page_crawled=callback)
        await crawler.crawl()

        assert len(callback_results) == 2

    async def test_normalizes_base_url(self, mock_aioresponse) -> None:
        """Test that base URL is normalized."""
        mock_aioresponse.get(
            "https://example.com/",
            body="<html><body><p>Home</p></body></html>",
            headers={"Content-Type": "text/html"},
        )

        # URL with trailing slash and fragment should be normalized
        crawler = Crawler("https://EXAMPLE.COM/#section")
        results = await crawler.crawl()

        assert len(results) == 1
        assert results[0].url == "https://example.com/"


class TestCrawlerConfig:
    """Tests for CrawlerConfig."""

    def test_default_values(self) -> None:
        config = CrawlerConfig()
        assert config.concurrency == 10
        assert config.timeout == 30
        assert config.max_pages is None
        assert config.user_agent == "WebCrawler/1.0"

    def test_custom_values(self) -> None:
        config = CrawlerConfig(
            concurrency=5,
            timeout=60,
            max_pages=100,
            user_agent="CustomBot/2.0",
        )
        assert config.concurrency == 5
        assert config.timeout == 60
        assert config.max_pages == 100
        assert config.user_agent == "CustomBot/2.0"


class TestCrawlResult:
    """Tests for CrawlResult dataclass."""

    def test_default_values(self) -> None:
        result = CrawlResult(url="https://example.com")
        assert result.url == "https://example.com"
        assert result.links == []
        assert result.error is None

    def test_with_links(self) -> None:
        result = CrawlResult(
            url="https://example.com",
            links=["https://example.com/a", "https://example.com/b"],
        )
        assert len(result.links) == 2

    def test_with_error(self) -> None:
        result = CrawlResult(url="https://example.com", error="Connection failed")
        assert result.error == "Connection failed"
