import pytest

from site_crawler.core.urls import (
    HostScope,
    host_key,
    normalise,
    resolve,
    resolve_and_normalise,
    same_host,
)
from site_crawler.models import ConfigError, parse_host_pattern


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("HTTPS://Example.COM:443/x#section", "https://example.com/x"),
        ("http://example.com:80", "http://example.com/"),
        ("http://example.com:8080/a?b=1&a=2", "http://example.com:8080/a?b=1&a=2"),
        ("https://example.com/a/", "https://example.com/a/"),  # trailing slash kept
        ("https://example.com/A", "https://example.com/A"),  # path case kept
        ("https://[::1]:8443/x", "https://[::1]:8443/x"),
    ],
)
def test_normalise(url: str, expected: str) -> None:
    assert normalise(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "mailto:hi@example.com",
        "tel:+441234",
        "javascript:void(0)",
        "ftp://example.com/",
        "data:text/plain,hi",
        "http://example.com:99999/",
        "/relative",
    ],
)
def test_normalise_rejects_non_http(url: str) -> None:
    assert normalise(url) is None


@pytest.mark.parametrize(
    ("base", "href", "expected"),
    [
        ("https://example.com/new/", "page", "https://example.com/new/page"),
        ("https://example.com/new/x", "../up", "https://example.com/up"),
        ("https://example.com/a", "//other.org/p", "https://other.org/p"),
        ("https://example.com/a", "?q=1", "https://example.com/a?q=1"),
        ("https://example.com/a", "#top", "https://example.com/a"),
        ("https://example.com/a", "  /b  ", "https://example.com/b"),
    ],
)
def test_resolve_and_normalise(base: str, href: str, expected: str) -> None:
    assert resolve_and_normalise(base, href) == expected


@pytest.mark.parametrize("href", ["", "   ", "mailto:x@y.z", "javascript:alert(1)"])
def test_resolve_and_normalise_drops_unusable(href: str) -> None:
    assert resolve_and_normalise("https://example.com/", href) is None


def test_resolve_empty() -> None:
    assert resolve("https://example.com/", "") is None


@pytest.mark.parametrize(
    ("url", "same"),
    [
        ("https://example.com/about", True),
        ("http://example.com/about", True),  # scheme ignored
        ("https://EXAMPLE.com:443/", True),
        ("https://example.com:8443/", False),
        ("https://www.example.com/", False),
        ("https://blog.example.com/", False),
        ("https://other.org/", False),
        ("https://example.com.evil.org/", False),
    ],
)
def test_same_host(url: str, same: bool) -> None:
    host = host_key("https://example.com/")
    assert host == "example.com"
    assert same_host(url, host) is same


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("docs.partner.io", "docs.partner.io"),
        ("  Docs.Partner.IO.  ", "docs.partner.io"),
        ("localhost:8001", "localhost:8001"),
        ("example.com:443", "example.com"),  # default port ignored
        ("10.0.0.1", "10.0.0.1"),
        ("[::1]:8080", "[::1]:8080"),
        ("*.example.com", "*.example.com"),
        ("*.Example.COM", "*.example.com"),
    ],
)
def test_parse_host_pattern(text: str, expected: str) -> None:
    assert str(parse_host_pattern(text)) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "*",
        "*.",
        "https://example.com",
        "example.com/path",
        "user@example.com",
        "exa*mple.com",
        "a.*.example.com",
        "*example.com",
        "*.example.com:8080",
        "*.10.0.0.1",
        "-bad.example.com",
        "bad_label.example.com",
        "two words.com",
    ],
)
def test_parse_host_pattern_rejects(text: str) -> None:
    with pytest.raises(ConfigError, match="invalid host pattern"):
        parse_host_pattern(text)


def test_invalid_pattern_error_names_it() -> None:
    with pytest.raises(ConfigError, match=r"'https://example\.com/x'"):
        parse_host_pattern("https://example.com/x")


def scope(*patterns: str) -> HostScope:
    return HostScope("https://example.com/", [parse_host_pattern(p) for p in patterns])


@pytest.mark.parametrize(
    ("url", "allowed"),
    [
        ("https://example.com/a", True),  # base host
        ("http://EXAMPLE.com:80/", True),  # case, scheme and default port ignored
        ("https://example.com:8443/", False),  # other port is another site
        ("https://www.example.com/", False),
        ("https://other.org/", False),
        ("mailto:x@example.com", False),
    ],
)
def test_scope_without_patterns_is_base_host_only(url: str, allowed: bool) -> None:
    assert scope().allows(url) is allowed


@pytest.mark.parametrize(
    ("url", "allowed"),
    [
        ("https://blog.example.com/", True),
        ("https://a.b.example.com/x", True),  # any depth
        ("https://BLOG.Example.com/", True),
        ("https://blog.example.com:8443/", False),  # wildcards cover default ports only
        ("https://notexample.com/", False),
        ("https://example.com.evil.org/", False),
        ("https://docs.partner.io/guide", True),
        ("https://www.docs.partner.io/", False),  # exact means exact
        ("http://localhost:8001/", True),
        ("http://localhost/", False),
        ("http://[::1]:8080/", True),
    ],
)
def test_scope_with_patterns(url: str, allowed: bool) -> None:
    patterns = ("*.example.com", "docs.partner.io", "localhost:8001", "[::1]:8080")
    assert scope(*patterns).allows(url) is allowed


def test_wildcard_does_not_cover_its_apex() -> None:
    other = HostScope("https://other.org/", [parse_host_pattern("*.example.com")])
    assert not other.allows("https://example.com/")
    assert other.allows("https://www.example.com/")
