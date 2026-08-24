from __future__ import annotations

from crawler.web.dom import extract_anchor_urls

PAGE = "http://h/dir/page"


def test_relative_and_absolute_resolved() -> None:
    html = b'<a href="a">A</a><a href="http://x/b">B</a>'
    assert extract_anchor_urls(html, PAGE) == ["http://h/dir/a", "http://x/b"]


def test_base_href_changes_resolution() -> None:
    html = b'<base href="http://h/base/"><a href="x">X</a>'
    assert extract_anchor_urls(html, PAGE) == ["http://h/base/x"]


def test_document_order_and_duplicates_kept() -> None:
    html = b'<a href="a">1</a><a href="b">2</a><a href="a">3</a>'
    assert extract_anchor_urls(html, "http://h/") == [
        "http://h/a",
        "http://h/b",
        "http://h/a",
    ]


def test_fragment_stripped_and_scheme_kept() -> None:
    html = b'<a href="p#top">P</a><a href="mailto:t@h">M</a>'
    assert extract_anchor_urls(html, "http://h/") == ["http://h/p", "mailto:t@h"]


def test_empty_and_whitespace_href_dropped() -> None:
    html = b'<a href="">empty</a><a href="   ">ws</a><a href="ok">ok</a>'
    assert extract_anchor_urls(html, "http://h/") == ["http://h/ok"]


def test_malformed_html_is_best_effort() -> None:
    assert extract_anchor_urls(b'<a href="a">unclosed', "http://h/") == ["http://h/a"]


def test_xml_declaration_does_not_crash() -> None:
    html = b'<?xml version="1.0" encoding="UTF-8"?><html><body><a href="a">A</a></body></html>'
    assert extract_anchor_urls(html, "http://h/") == ["http://h/a"]


def test_empty_document_yields_no_links() -> None:
    assert extract_anchor_urls(b"", "http://h/") == []
    assert extract_anchor_urls(b"   ", "http://h/") == []
