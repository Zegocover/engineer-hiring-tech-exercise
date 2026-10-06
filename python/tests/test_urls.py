import pytest

from site_crawler.core.urls import host_key, normalise, resolve, resolve_and_normalise, same_host


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
