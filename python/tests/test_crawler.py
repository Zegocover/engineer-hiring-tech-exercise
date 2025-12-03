from unittest.mock import MagicMock
from crawler.crawler import PooledCrawler


def make_crawler(url: str = "http://target.com") -> PooledCrawler:
    session = MagicMock()
    return PooledCrawler(url=url, workers=1, session=session)


def test_extract_links_filters_invalid_href():
    crawler = make_crawler()

    html = """
    <html>
      <body>
        <a href="https://other.com/page">External domain</a>
        <a href="https://sub.target.com/page">Sub domain</a>
        <a href="mailto:someone@target.com">Mail link</a>
        <a href="tel:+123456789">Tel link</a>
        <a href="javascript:void(0)">JS link</a>
        <a href="#section">Section</a>
        <a href="">Empty href</a>
        <a href="   ">Whitespace href</a>
        <link href="/should-not-be-picked" />
        <div href="/also-ignored">Not an anchor</div>
        <a>Missing href</a>
      </body>
    </html>
    """

    result = crawler.extract_links(html)
    assert len(result) == 0


def test_extract_links_handles_relative_and_absolute_hrefs():
    crawler = make_crawler("https://target.com/base")

    html = """
    <html>
      <body>
        <a href="/absolute-path">Absolute path</a>
        <a href="relative-path">Relative path</a>
        <a href="https://target.com/absolute-path-1">Absolute path 1</a>
        <a href="https://target.com/path/absolute-path-2">Absolute path 2</a>
        <a href="../relative-path-1">Relative path 1</a>
        <a href="path/relative-path-2">Relative path 1</a>
        <a href="./relative-path-3">Relative path 1</a>
      </body>
    </html>
    """

    result = sorted(crawler.extract_links(html))
    expected = sorted([
        "https://target.com/absolute-path",
        "https://target.com/base/relative-path",
        "https://target.com/absolute-path-1",
        "https://target.com/path/absolute-path-2",
        "https://target.com/relative-path-1",
        "https://target.com/base/path/relative-path-2",
        "https://target.com/base/relative-path-3",
    ])
    assert result == expected


def test_extract_links_strips_trailing_slashes_and_deduplicates():
    crawler = make_crawler()

    html = """
    <html>
      <body>
        <a href="http://target.com/page/">With trailing slash</a>
        <a href="http://target.com/page">Without trailing slash</a>
        <a href="/page/">With trailing slash</a>
        <a href="/page">Without trailing slash</a>
      </body>
    </html>
    """

    result = crawler.extract_links(html)
    assert result == ["http://target.com/page"]