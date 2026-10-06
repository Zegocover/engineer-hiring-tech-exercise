from __future__ import annotations

from site_crawler.models import FetchResult
from site_crawler.parsers import SelectolaxParser

URL = "https://example.com/dir/page"


def parse(html: str, url: str = URL) -> list[str]:
    return SelectolaxParser().parse(FetchResult(url, url, 200, "text/html", html.encode()))


def test_anchors_in_document_order() -> None:
    html = """
    <html><body>
      <nav><a href="/home">Home</a></nav>
      <p>See <a href="other">other</a> and <a href="https://ext.org/">ext</a>.</p>
      <a href="/home">again</a>
    </body></html>
    """
    assert parse(html) == ["/home", "other", "https://ext.org/", "/home"]


def test_ignores_anchors_without_href_and_other_tags() -> None:
    html = """
    <a name="top">x</a><a href="">empty</a><a href="   ">blank</a>
    <link href="/style.css"><img src="/i.png"><script src="/s.js"></script>
    <a href="/real">real</a>
    """
    assert parse(html) == ["/real"]


def test_malformed_html() -> None:
    # Unquoted/mixed-case attributes, unclosed elements, stray table content.
    html = "<div><a href=/one>one</a><p><a HREF='/two'>two</a></div><table><a href=/three>3</a>"
    assert parse(html) == ["/one", "/two", "/three"]


def test_base_href_applied() -> None:
    html = '<head><base href="/assets/"></head><body><a href="x">x</a><a href="/y">y</a></body>'
    assert parse(html) == ["https://example.com/assets/x", "https://example.com/y"]


def test_absolute_base_href() -> None:
    html = '<base href="https://cdn.example.com/b/"><a href="z">z</a>'
    assert parse(html) == ["https://cdn.example.com/b/z"]


def test_non_utf8_bytes_do_not_crash() -> None:
    body = b'<a href="/caf\xe9">x</a>'
    result = SelectolaxParser().parse(FetchResult(URL, URL, 200, "text/html", body))
    assert len(result) == 1
