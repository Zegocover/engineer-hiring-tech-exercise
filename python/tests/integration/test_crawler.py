"""Integration tests for the crawler using a local test server."""

import pytest
from pytest_httpserver import HTTPServer

from crawler.crawler import Crawler


@pytest.fixture(scope="session")
def httpserver_listen_address() -> tuple[str, int]:
    return ("127.0.0.1", 8888)


async def test_crawler_crawls_single_page(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/").respond_with_data(
        "<html><body><h1>Home</h1></body></html>",
        content_type="text/html",
    )

    crawler = Crawler(httpserver.url_for("/"))
    results = await crawler.crawl()

    assert len(results) == 1
    assert httpserver.url_for("/") in results


async def test_crawler_follows_links(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/").respond_with_data(
        '<html><body><a href="/about">About</a></body></html>',
        content_type="text/html",
    )
    httpserver.expect_request("/about").respond_with_data(
        "<html><body><h1>About</h1></body></html>",
        content_type="text/html",
    )

    crawler = Crawler(httpserver.url_for("/"))
    results = await crawler.crawl()

    assert len(results) == 2
    assert httpserver.url_for("/") in results
    assert httpserver.url_for("/about") in results


async def test_crawler_does_not_revisit_pages(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/").respond_with_data(
        '<html><body><a href="/about">About</a></body></html>',
        content_type="text/html",
    )
    httpserver.expect_request("/about").respond_with_data(
        '<html><body><a href="/">Home</a></body></html>',
        content_type="text/html",
    )

    crawler = Crawler(httpserver.url_for("/"))
    results = await crawler.crawl()

    # Should only crawl 2 pages, not 3
    assert len(results) == 2


async def test_crawler_ignores_external_links(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/").respond_with_data(
        '<html><body><a href="https://external.com">External</a></body></html>',
        content_type="text/html",
    )

    crawler = Crawler(httpserver.url_for("/"))
    results = await crawler.crawl()

    assert len(results) == 1
    assert "external.com" not in str(results)


async def test_crawler_handles_missing_pages(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/").respond_with_data(
        '<html><body><a href="/missing">Missing</a></body></html>',
        content_type="text/html",
    )
    httpserver.expect_request("/missing").respond_with_data("Not Found", status=404)

    crawler = Crawler(httpserver.url_for("/"))
    results = await crawler.crawl()

    assert len(results) == 2
    assert results[httpserver.url_for("/missing")] == []


async def test_crawler_records_found_urls(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/").respond_with_data(
        '<html><body><a href="/a">A</a><a href="/b">B</a></body></html>',
        content_type="text/html",
    )
    httpserver.expect_request("/a").respond_with_data(
        "<html><body>A</body></html>",
        content_type="text/html",
    )
    httpserver.expect_request("/b").respond_with_data(
        "<html><body>B</body></html>",
        content_type="text/html",
    )

    crawler = Crawler(httpserver.url_for("/"))
    results = await crawler.crawl()

    home_url = httpserver.url_for("/")
    assert httpserver.url_for("/a") in results[home_url]
    assert httpserver.url_for("/b") in results[home_url]
