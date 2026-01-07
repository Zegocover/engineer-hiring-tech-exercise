"""Tests for HTML parser."""

from crawler.parser import extract_links


def test_extracts_href_from_anchors() -> None:
    html = '<html><body><a href="/about">About</a><a href="/contact">Contact</a></body></html>'
    assert extract_links(html) == ["/about", "/contact"]


def test_ignores_anchors_without_href() -> None:
    html = '<html><body><a name="top">Top</a><a href="/page">Page</a></body></html>'
    assert extract_links(html) == ["/page"]


def test_ignores_empty_href() -> None:
    html = """<html><body>
        <a href="">Empty</a>
        <a href="   ">Whitespace</a>
        <a href="/valid">Valid</a>
    </body></html>"""
    assert extract_links(html) == ["/valid"]


def test_handles_malformed_html() -> None:
    html = '<html><body><a href="/page"><div>Nested</a></body></html>'
    assert extract_links(html) == ["/page"]


def test_returns_empty_list_for_no_links() -> None:
    html = "<html><body><p>No links here</p></body></html>"
    assert extract_links(html) == []
