"""Unit tests for the core crawler module."""


import pytest
from aioresponses import aioresponses

from crawler.crawler import Crawler, PageResult


@pytest.fixture
def mock_aiohttp():
    """Provide an aioresponses context manager for mocking HTTP."""
    with aioresponses() as m:
        yield m


def make_html(links: list[str], title: str = "Test") -> str:
    """Helper to generate simple HTML with given links."""
    anchors = "\n".join(f'<a href="{link}">{link}</a>' for link in links)
    return f"""
    <!DOCTYPE html>
    <html><head><title>{title}</title></head>
    <body>{anchors}</body></html>
    """


class TestCrawler:
    """Tests for the Crawler class."""

    @pytest.mark.asyncio
    async def test_crawls_single_page(self, mock_aiohttp):
        """Crawler fetches the starting page and reports its links."""
        html = make_html(["/about", "/contact"])
        mock_aiohttp.get("https://example.com/", payload=None, body=html,
                         headers={"Content-Type": "text/html"})

        crawler = Crawler("https://example.com", max_concurrency=2)

        # Mock the discovered pages too (they'll be found)
        mock_aiohttp.get("https://example.com/about", body="<html></html>",
                         headers={"Content-Type": "text/html"})
        mock_aiohttp.get("https://example.com/contact", body="<html></html>",
                         headers={"Content-Type": "text/html"})

        results = await crawler.crawl()

        urls_crawled = {r.url for r in results}
        assert "https://example.com/" in urls_crawled
        assert "https://example.com/about" in urls_crawled
        assert "https://example.com/contact" in urls_crawled

    @pytest.mark.asyncio
    async def test_does_not_crawl_external_domains(self, mock_aiohttp):
        """Crawler does not follow links to other domains."""
        html = make_html(["https://other.com/page", "/internal"])
        mock_aiohttp.get("https://example.com/", body=html,
                         headers={"Content-Type": "text/html"})
        mock_aiohttp.get("https://example.com/internal", body="<html></html>",
                         headers={"Content-Type": "text/html"})

        crawler = Crawler("https://example.com")
        results = await crawler.crawl()

        urls_crawled = {r.url for r in results}
        assert "https://other.com/page" not in urls_crawled

    @pytest.mark.asyncio
    async def test_does_not_crawl_subdomains(self, mock_aiohttp):
        """Crawler does not follow links to subdomains."""
        html = make_html(["https://sub.example.com/page", "/internal"])
        mock_aiohttp.get("https://example.com/", body=html,
                         headers={"Content-Type": "text/html"})
        mock_aiohttp.get("https://example.com/internal", body="<html></html>",
                         headers={"Content-Type": "text/html"})

        crawler = Crawler("https://example.com")
        results = await crawler.crawl()

        urls_crawled = {r.url for r in results}
        assert "https://sub.example.com/page" not in urls_crawled

    @pytest.mark.asyncio
    async def test_does_not_revisit_pages(self, mock_aiohttp):
        """Crawler visits each URL only once even if linked from multiple pages."""
        page_a = make_html(["/b", "/c"])
        page_b = make_html(["/a", "/c"])  # links back to a and to c
        page_c = make_html(["/a"])

        mock_aiohttp.get("https://example.com/a", body=page_a,
                         headers={"Content-Type": "text/html"})
        mock_aiohttp.get("https://example.com/b", body=page_b,
                         headers={"Content-Type": "text/html"})
        mock_aiohttp.get("https://example.com/c", body=page_c,
                         headers={"Content-Type": "text/html"})

        crawler = Crawler("https://example.com/a", max_concurrency=2)
        results = await crawler.crawl()

        urls_crawled = [r.url for r in results]
        # Each URL should appear exactly once
        assert len(urls_crawled) == len(set(urls_crawled))
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_handles_non_html_content(self, mock_aiohttp):
        """Crawler gracefully handles non-HTML responses."""
        html = make_html(["/image.pdf"])
        mock_aiohttp.get("https://example.com/", body=html,
                         headers={"Content-Type": "text/html"})
        mock_aiohttp.get("https://example.com/image.pdf", body=b"PDF content",
                         headers={"Content-Type": "application/pdf"})

        crawler = Crawler("https://example.com")
        results = await crawler.crawl()

        pdf_result = next(r for r in results if r.url == "https://example.com/image.pdf")
        assert pdf_result.error is not None
        assert "non-html" in pdf_result.error

    @pytest.mark.asyncio
    async def test_handles_timeout(self, mock_aiohttp):
        """Crawler handles request timeouts gracefully."""
        mock_aiohttp.get("https://example.com/", exception=TimeoutError())

        crawler = Crawler("https://example.com", timeout=1)
        results = await crawler.crawl()

        assert len(results) == 1
        assert results[0].error == "timeout"

    @pytest.mark.asyncio
    async def test_handles_connection_error(self, mock_aiohttp):
        """Crawler handles connection errors gracefully."""
        from aiohttp import ClientConnectionError

        mock_aiohttp.get("https://example.com/",
                         exception=ClientConnectionError("Connection refused"))

        crawler = Crawler("https://example.com")
        results = await crawler.crawl()

        assert len(results) == 1
        assert results[0].error is not None

    @pytest.mark.asyncio
    async def test_callback_invoked(self, mock_aiohttp):
        """The on_page_crawled callback is called for each page."""
        mock_aiohttp.get("https://example.com/", body="<html></html>",
                         headers={"Content-Type": "text/html"})

        callback_results: list[PageResult] = []
        crawler = Crawler(
            "https://example.com",
            on_page_crawled=callback_results.append,
        )
        await crawler.crawl()

        assert len(callback_results) == 1
        assert callback_results[0].url == "https://example.com/"

    @pytest.mark.asyncio
    async def test_stats(self, mock_aiohttp):
        """get_stats returns correct aggregated counts."""
        html = make_html(["/page2", "https://other.com/ext"])
        mock_aiohttp.get("https://example.com/", body=html,
                         headers={"Content-Type": "text/html"})
        mock_aiohttp.get("https://example.com/page2", body="<html></html>",
                         headers={"Content-Type": "text/html"})

        crawler = Crawler("https://example.com")
        await crawler.crawl()

        stats = crawler.get_stats()
        assert stats.pages_crawled == 2
        assert stats.pages_failed == 0

    @pytest.mark.asyncio
    async def test_deep_crawl(self, mock_aiohttp):
        """Crawler follows chains of links across multiple levels."""
        mock_aiohttp.get("https://example.com/", body=make_html(["/level1"]),
                         headers={"Content-Type": "text/html"})
        mock_aiohttp.get("https://example.com/level1", body=make_html(["/level2"]),
                         headers={"Content-Type": "text/html"})
        mock_aiohttp.get("https://example.com/level2", body=make_html(["/level3"]),
                         headers={"Content-Type": "text/html"})
        mock_aiohttp.get("https://example.com/level3", body="<html></html>",
                         headers={"Content-Type": "text/html"})

        crawler = Crawler("https://example.com", max_concurrency=2)
        results = await crawler.crawl()

        urls = {r.url for r in results}
        assert urls == {
            "https://example.com/",
            "https://example.com/level1",
            "https://example.com/level2",
            "https://example.com/level3",
        }
