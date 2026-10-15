"""StdlibHtmlParser: the library's parser cases, plus parity with DefaultSelectolaxParser."""

import pytest
from site_crawler import DefaultSelectolaxParser
from site_crawler.interfaces import Parser
from site_crawler.models import FetchResult

from crawler_api.adapters import StdlibHtmlParser

URL = "https://example.com/dir/page"


def parse(html: str, url: str = URL) -> list[str]:
    return StdlibHtmlParser().parse(FetchResult(url, url, 200, "text/html", html.encode()))


def test_matches_the_parser_protocol() -> None:
    parser: Parser = StdlibHtmlParser()
    assert parser.parse(FetchResult(URL, URL, 200, "text/html", b"")) == []


# --- The library's DefaultSelectolaxParser cases, same inputs and expectations ---


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
    result = StdlibHtmlParser().parse(FetchResult(URL, URL, 200, "text/html", body))
    assert len(result) == 1


# --- Parity: the same input through both parsers gives the same links ---

PARITY_CASES: dict[str, tuple[bytes, str]] = {
    "base after anchors": (b'<a href="x">x</a><base href="/b/"><a href="y">y</a>', "text/html"),
    "two bases, first wins": (b'<base href="/1/"><base href="/2/"><a href="x">x</a>', "text/html"),
    "first base has empty href": (b'<base href=""><base href="/2/"><a href="x">x</a>', "text/html"),
    "base without href is skipped": (
        b'<base target="_blank"><base href="/2/"><a href="x">x</a>',
        "text/html",
    ),
    "entities in href": (b'<a href="/q?a=1&amp;b=2">x</a><a href="/s&#32;p">y</a>', "text/html"),
    "anchor in comment": (b'<!-- <a href="/hidden">h</a> --><a href="/shown">s</a>', "text/html"),
    "anchor in script": (
        b'<script>var s = \'<a href="/js">j</a>\';</script><a href="/real">r</a>',
        "text/html",
    ),
    "anchor in style": (b'<style>/* <a href="/css"> */</style><a href="/real">r</a>', "text/html"),
    "anchor in template": (
        b'<template><a href="/tpl">t</a><base href="/b/"></template><a href="x">r</a>',
        "text/html",
    ),
    "nested templates": (
        b'<template><template><a href="/2">t</a></template><a href="/1">t</a></template>'
        b'<a href="/real">r</a>',
        "text/html",
    ),
    "anchor in textarea": (
        b'<textarea><a href="/ta">t</a></textarea><a href="/r">r</a>',
        "text/html",
    ),
    "anchor in noscript": (b'<noscript><a href="/ns">n</a></noscript>', "text/html"),
    "self-closing anchor": (b'<a href="/self"/><a href="/next">n</a>', "text/html"),
    "uppercase tags": (b'<A HREF="/upper">U</A>', "text/html"),
    "nested and unclosed": (
        b'<ul><li><a href="/a">a<li><a href="/b">b</ul><p><a href=/c>c',
        "text/html",
    ),
    "svg xlink:href ignored": (
        b'<svg><a xlink:href="/svg">s</a></svg><a href="/r">r</a>',
        "text/html",
    ),
    "svg plain href": (b'<svg><a href="/svg2">s</a></svg>', "text/html"),
    "duplicate href attributes": (b'<a href="/first" href="/second">d</a>', "text/html"),
    "whitespace around href": (b'<a href="\n  /spaced  \n">s</a>', "text/html"),
    "href without value": (b'<a href>empty</a><a href="/real">r</a>', "text/html"),
    "area tag ignored": (b'<map><area href="/area"></map><a href="/real">r</a>', "text/html"),
    "non-http schemes kept": (
        b'<a href="javascript:void(0)">j</a><a href="mailto:a@b.c">m</a>',
        "text/html",
    ),
    "utf-8 non-ascii": ('<a href="/naïve">n</a>'.encode(), "text/html; charset=utf-8"),
    "utf-8 byte order mark": (b'\xef\xbb\xbf<a href="/bom">b</a>', "text/html"),
    "unknown charset label": (b'<a href="/x">x</a>', "text/html; charset=bogus"),
    "charset only in meta tag": (
        '<meta charset="iso-8859-1"><a href="/café">c</a>'.encode("latin-1"),
        "text/html",
    ),
}


@pytest.mark.parametrize(("body", "content_type"), PARITY_CASES.values(), ids=PARITY_CASES.keys())
def test_same_links_as_selectolax(body: bytes, content_type: str) -> None:
    page = FetchResult(URL, URL, 200, content_type, body)
    assert StdlibHtmlParser().parse(page) == DefaultSelectolaxParser().parse(page)


def test_known_difference_charset_from_the_content_type_header() -> None:
    # Expected difference, in this parser's favour: it decodes with the charset the server
    # sends in Content-Type. selectolax ignores that header and decodes the latin-1 byte as
    # UTF-8, turning "é" into a replacement character.
    page = FetchResult(
        URL, URL, 200, "text/html; charset=ISO-8859-1", '<a href="/café">c</a>'.encode("latin-1")
    )
    assert StdlibHtmlParser().parse(page) == ["/café"]
    assert DefaultSelectolaxParser().parse(page) == ["/caf\ufffd"]
