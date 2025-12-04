import pytest
from typing import Set

from site_crawler.extractor import get_urls_from_html


@pytest.mark.parametrize(
    "html,base,expected",
    [
        # relative path with fragment -> fragment removed
        ("<a href=\"/about#team\">About</a>", "https://example.com/", {"https://example.com/about"}),

        # absolute link without path -> root path '/' normalized
        ("<a href=\"https://example.com\">Home</a>", "https://example.com/", {"https://example.com/"}),

        # non-http schemes (mailto) are filtered out
        ("<a href=\"mailto:me@example.com\">Mail</a>", "https://example.com/", set()),

        # mixed schemes: only http/https preserved, relative resolved
        (
            "<a href=\"javascript:void(0)\">x</a>"
            "<a href=\"ftp://example.com/file\">f</a>"
            "<a href=\"/contact\">c</a>",
            "https://example.com/",
            {"https://example.com/contact"},
        ),

        # duplicates and fragments with query preserved -> single normalized URL
        (
            "<a href=\"/search?q=hi#frag\">s1</a><a href=\"/search?q=hi\">s2</a>",
            "https://example.com/",
            {"https://example.com/search?q=hi"},
        ),
    ],
)
def test_get_urls_from_html_parametrized(html: str, base: str, expected: Set[str]) -> None:
    got = get_urls_from_html(html, base)
    assert got == expected
