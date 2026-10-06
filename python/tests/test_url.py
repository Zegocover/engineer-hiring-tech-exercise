"""Tests for the pure URL logic. These cover the normalization policy,
scheme filtering and domain scoping — the parts of the crawler most prone
to subtle correctness bugs.
"""

from __future__ import annotations

import pytest

from crawler.url import get_host, is_http_url, normalize, same_site

# ---------------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Fragments are stripped.
        ("http://example.com/page#section", "http://example.com/page"),
        ("http://example.com/#top", "http://example.com/"),
        # Scheme and host are lower-cased; path and query keep their case.
        ("HTTP://Example.COM/Path?Q=V", "http://example.com/Path?Q=V"),
        # Empty path becomes "/".
        ("http://example.com", "http://example.com/"),
        # Default ports are dropped; non-default ports are kept.
        ("http://example.com:80/", "http://example.com/"),
        ("https://example.com:443/", "https://example.com/"),
        ("http://example.com:8080/", "http://example.com:8080/"),
        # Dot segments are resolved.
        ("http://example.com/a/./b", "http://example.com/a/b"),
        ("http://example.com/a/../b", "http://example.com/b"),
        ("http://example.com/a/b/../../c", "http://example.com/c"),
        # A trailing dot on the host is removed.
        ("http://example.com./page", "http://example.com/page"),
        # Trailing slashes are preserved (treated as potentially distinct).
        ("http://example.com/about/", "http://example.com/about/"),
        ("http://example.com/about", "http://example.com/about"),
        # Query strings are preserved verbatim (order not normalized).
        ("http://example.com/s?b=2&a=1", "http://example.com/s?b=2&a=1"),
        # Leading relative dot segments are discarded (RFC 3986 §5.2.4).
        ("http://example.com/../a", "http://example.com/a"),
        ("http://example.com/./a", "http://example.com/a"),
        # A path that is only dot segments collapses away.
        ("http://example.com/a/..", "http://example.com/"),
        ("http://example.com/a/.", "http://example.com/a/"),
        # IPv6 literal hosts keep their brackets and drop the default port.
        ("http://[::1]:80/a", "http://[::1]/a"),
        ("http://[2001:db8::1]:8080/a", "http://[2001:db8::1]:8080/a"),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Leading dot prefixes are discarded but the real segment survives.
        ("../a", "a"),
        ("./a", "a"),
        # A path that is nothing but dot segments resolves to empty.
        (".", ""),
        ("..", ""),
    ],
)
def test_normalize_bare_relative_dot_segments(raw: str, expected: str) -> None:
    # No authority to anchor against, so no leading "/" is added.
    assert normalize(raw) == expected


def test_normalize_is_idempotent() -> None:
    once = normalize("HTTP://Example.com:80/a/../b#x")
    assert normalize(once) == once


def test_normalize_collapses_trivial_duplicates() -> None:
    a = normalize("http://Example.com")
    b = normalize("http://example.com:80/")
    c = normalize("http://example.com/#frag")
    assert a == b == c == "http://example.com/"


# ---------------------------------------------------------------------------
# is_http_url
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://example.com", True),
        ("https://example.com/x", True),
        ("HTTPS://EXAMPLE.COM", True),
        ("mailto:hi@example.com", False),
        ("tel:+441234567890", False),
        ("javascript:void(0)", False),
        ("data:text/plain,hello", False),
        ("ftp://example.com/file", False),
        ("/relative/path", False),  # relative: no scheme
        ("#fragment-only", False),
    ],
)
def test_is_http_url(url: str, expected: bool) -> None:
    assert is_http_url(url) is expected


# ---------------------------------------------------------------------------
# get_host
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://example.com/x", "example.com"),
        ("http://www.example.com/x", "example.com"),  # www stripped
        ("http://WWW.Example.COM/x", "example.com"),
        ("http://blog.example.com/x", "blog.example.com"),
        ("https://example.com:8443/x", "example.com"),
        ("/relative", None),
        ("mailto:hi@example.com", None),
    ],
)
def test_get_host(url: str, expected: str | None) -> None:
    assert get_host(url) == expected


# ---------------------------------------------------------------------------
# same_site
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "base_host", "expected"),
    [
        # Apex and www are the same site.
        ("http://example.com/a", "example.com", True),
        ("http://www.example.com/a", "example.com", True),
        ("http://example.com/a", "www.example.com", True),
        ("https://example.com/a", "example.com", True),  # scheme-agnostic
        # Other subdomains are excluded by default.
        ("http://blog.example.com/a", "example.com", False),
        ("http://api.example.com/a", "example.com", False),
        # Different registrable domains are excluded.
        ("http://other.com/a", "example.com", False),
        # Look-alike hosts must not match.
        ("http://notexample.com/a", "example.com", False),
        ("http://example.com.evil.com/a", "example.com", False),
        # No host at all.
        ("mailto:hi@example.com", "example.com", False),
        ("/relative", "example.com", False),
    ],
)
def test_same_site_default(url: str, base_host: str, expected: bool) -> None:
    assert same_site(url, base_host) is expected


@pytest.mark.parametrize(
    ("url", "base_host", "expected"),
    [
        ("http://example.com/a", "example.com", True),
        ("http://www.example.com/a", "example.com", True),
        ("http://blog.example.com/a", "example.com", True),  # now included
        ("http://deep.blog.example.com/a", "example.com", True),
        ("http://other.com/a", "example.com", False),
        ("http://notexample.com/a", "example.com", False),
        ("http://example.com.evil.com/a", "example.com", False),
    ],
)
def test_same_site_include_subdomains(url: str, base_host: str, expected: bool) -> None:
    assert same_site(url, base_host, include_subdomains=True) is expected
