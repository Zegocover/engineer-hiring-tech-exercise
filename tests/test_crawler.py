from site_crawler.crawler import Crawler


async def test_crawls_exact_host_and_reports_offsite_links(serve):
    start = await serve([
        ("/", '<a href="/a">a</a><a href="https://blog.example.com/nope">sub</a><a href="https://other.test/nope">off</a>', 200),
        ("/a", '<a href="/">home</a>', 200),
    ])
    pages = await Crawler(concurrency=4).crawl(start)
    crawled = {page.url for page in pages}
    assert len(crawled) == 2
    assert all("blog.example.com" not in url and "other.test" not in url for url in crawled)

    home = next(page for page in pages if any("other.test" in link for link in page.links))
    assert any("blog.example.com" in link for link in home.links)
    assert any(link.rstrip("/").endswith("/a") for link in home.links)


async def test_circular_links_are_fetched_once(serve):
    start = await serve([
        ("/", '<a href="/b">b</a>', 200),
        ("/b", '<a href="/">home</a>', 200),
    ])
    pages = await Crawler(concurrency=2).crawl(start)
    assert len(pages) == 2
    assert {page.url.rstrip("/") for page in pages} == {
        start.rstrip("/"),
        start.rstrip("/") + "/b",
    }


async def test_follows_nested_pages_until_the_frontier_is_empty(serve):
    start = await serve([
        ("/", '<a href="/a">a</a>', 200),
        ("/a", '<a href="/a/b">b</a>', 200),
        ("/a/b", "<p>end</p>", 200),
    ])
    pages = await Crawler(concurrency=2).crawl(start)
    assert len(pages) == 3
    assert all(not page.error for page in pages)


async def test_http_errors_are_recorded_without_failing_the_crawl(serve):
    start = await serve([
        ("/", '<a href="/missing">missing</a>', 200),
        ("/missing", "", 404),
    ])
    pages = await Crawler(concurrency=2).crawl(start)
    missing = next(page for page in pages if page.url.rstrip("/").endswith("/missing"))
    assert missing.error == "HTTP 404"
    assert missing.links == []
