from crawler.src.extractor import LinkContentExtractor

extract_links = LinkContentExtractor().extract_content

BASE_URL = "https://example.com"


def test_extracts_absolute_and_relative_links() -> None:
    html = """
    <html><body>
        <a href="https://example.com/a">A</a>
        <a href="/b">B</a>
        <a href="c">C</a>
    </body></html>
    """
    links = extract_links(html, BASE_URL)
    assert links == [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
    ]


def test_ignores_anchors_without_href() -> None:
    html = '<html><body><a name="top">No href</a></body></html>'
    assert extract_links(html, BASE_URL) == []


def test_ignores_non_http_schemes() -> None:
    html = """
    <html><body>
        <a href="mailto:a@example.com">Mail</a>
        <a href="javascript:void(0)">JS</a>
        <a href="/ok">OK</a>
    </body></html>
    """
    assert extract_links(html, BASE_URL) == ["https://example.com/ok"]


def test_drops_fragment_only_links() -> None:
    # A fragment-only href resolves back to the current page itself, so it's
    # dropped as a self-link, not reported as a "found" link.
    html = '<html><body><a href="#section">Jump</a></body></html>'
    assert extract_links(html, BASE_URL) == []


def test_empty_html_returns_no_links() -> None:
    assert extract_links("", BASE_URL) == []


def test_ignores_self_referential_links() -> None:
    html = """
    <html><body>
        <a href="https://example.com">Home</a>
        <a href="/">Also home</a>
        <a href="/other">Other</a>
    </body></html>
    """
    assert extract_links(html, BASE_URL) == ["https://example.com/other"]


def test_deduplicates_repeated_links() -> None:
    html = """
    <html><body>
        <a href="/page">Nav link</a>
        <a href="/page">Footer link</a>
        <a href="https://example.com/page">Same link, absolute form</a>
    </body></html>
    """
    assert extract_links(html, BASE_URL) == ["https://example.com/page"]
