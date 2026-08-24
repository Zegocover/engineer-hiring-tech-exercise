from __future__ import annotations

import pytest

from crawler.web import urls


@pytest.mark.parametrize(
    ("base", "href", "expected"),
    [
        ("http://a.com/p/q", "x", "http://a.com/p/x"),
        ("http://a.com/p/", "/y#frag", "http://a.com/y"),
        ("http://a.com/p/", "//b.com/z#sec", "http://b.com/z"),
        ("http://a.com/p/q/", "../up", "http://a.com/p/up"),
        ("http://a.com/p/", "http://b.com/z#sec", "http://b.com/z"),
        ("http://a.com/", "mailto:x@a.com", "mailto:x@a.com"),
    ],
)
def test_absolutize(base: str, href: str, expected: str) -> None:
    assert urls.absolutize(base, href) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://a.com/x", True),
        ("https://a.com/x", True),
        ("mailto:x@a.com", False),
        ("tel:+123", False),
        ("javascript:void(0)", False),
        ("ftp://a.com/x", False),
    ],
)
def test_is_http(url: str, expected: bool) -> None:
    assert urls.is_http(url) is expected


@pytest.mark.parametrize(
    ("url", "base_host", "expected"),
    [
        ("http://a.com/x", "a.com", True),
        ("http://A.com/x", "a.com", True),
        ("http://a.com:8080/x", "a.com", True),
        ("http://sub.a.com/x", "a.com", False),
        ("http://b.com/x", "a.com", False),
        ("mailto:x@a.com", "a.com", False),
    ],
)
def test_same_host(url: str, base_host: str, expected: bool) -> None:
    assert urls.same_host(url, base_host) is expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://a.com/x", True),
        ("https://a.com", True),
        ("a.com/x", False),
        ("/relative", False),
        ("mailto:x@a.com", False),
        ("http://a.com:bad", False),
        ("http://[::1", False),
    ],
)
def test_is_absolute_http(url: str, expected: bool) -> None:
    assert urls.is_absolute_http(url) is expected


def test_dedup_key_canonicalises() -> None:
    key = urls.dedup_key
    assert key("http://a.com/p#one") == key("http://a.com/p#two")  # fragment dropped
    assert key("http://a.com/p") != key("http://a.com/p/")  # trailing slash significant
    assert key("http://a.com") == key("http://a.com/")  # empty path is root
    assert key("http://A.COM/x") == key("http://a.com/x")  # host case-insensitive
    assert key("HTTP://a.com/x") == key("http://a.com/x")  # scheme case-insensitive
    assert key("http://a.com/a%2Fb") != key("http://a.com/a/b")  # encoded slash is data


def test_robots_url() -> None:
    assert urls.robots_url("http://a.com/deep/path?q=1") == "http://a.com/robots.txt"
    assert urls.robots_url("https://a.com:8443/x") == "https://a.com:8443/robots.txt"
