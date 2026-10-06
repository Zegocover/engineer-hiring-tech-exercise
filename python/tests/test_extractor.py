"""Tests for LinkExtractor."""

from __future__ import annotations

from crawler.extractor import LinkExtractor

PAGE = "https://example.com/dir/page"


def extract(html: str, page_url: str = PAGE) -> tuple[str, ...]:
    return LinkExtractor().extract(page_url, html)


def test_resolves_absolute_relative_root_and_protocol_relative() -> None:
    html = """
        <a href="https://other.com/abs">absolute</a>
        <a href="sibling">relative</a>
        <a href="/root">root-relative</a>
        <a href="//cdn.example.com/proto">protocol-relative</a>
    """
    assert extract(html) == (
        "https://other.com/abs",
        "https://example.com/dir/sibling",
        "https://example.com/root",
        "https://cdn.example.com/proto",
    )


def test_deduplicates_preserving_first_seen_order() -> None:
    html = """
        <a href="/a">1</a>
        <a href="/b">2</a>
        <a href="/a">duplicate of 1</a>
    """
    assert extract(html) == ("https://example.com/a", "https://example.com/b")


def test_filters_out_non_http_schemes() -> None:
    html = """
        <a href="mailto:hi@example.com">mail</a>
        <a href="tel:+441234567890">phone</a>
        <a href="javascript:void(0)">js</a>
        <a href="/keep">keep</a>
    """
    assert extract(html) == ("https://example.com/keep",)


def test_fragment_links_are_kept_faithfully() -> None:
    # Fragments are part of what the page links to; the crawler strips them
    # later when scheduling, but the extractor reports them as found.
    html = '<a href="#section">jump</a><a href="/p#top">p</a>'
    assert extract(html) == (
        "https://example.com/dir/page#section",
        "https://example.com/p#top",
    )


def test_skips_empty_and_whitespace_hrefs() -> None:
    html = '<a href="">empty</a><a href="   ">spaces</a><a href="  /trim  ">padded</a>'
    assert extract(html) == ("https://example.com/trim",)


def test_honours_base_href_for_relative_links() -> None:
    html = """
        <head><base href="https://example.com/other/"></head>
        <body>
          <a href="rel">relative resolves against base</a>
          <a href="/root">root ignores base path</a>
        </body>
    """
    assert extract(html) == (
        "https://example.com/other/rel",
        "https://example.com/root",
    )


def test_handles_malformed_html() -> None:
    html = "<html><body><a href='/x'>unclosed <a href='/y'>tags"
    assert extract(html) == ("https://example.com/x", "https://example.com/y")


def test_returns_empty_when_no_links() -> None:
    assert extract("<html><body><p>no links here</p></body></html>") == ()
