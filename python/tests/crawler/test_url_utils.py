import pytest
from crawler.url_utils import (
    normalize_url,
    get_domain,
    is_same_domain,
    resolve_links,
)


def test_normalize_url():
    assert (
        normalize_url("https://example.com/path/") == "https://example.com/path"
    )
    assert (
        normalize_url("https://example.com/path//#anchor")
        == "https://example.com/path"
    )
    assert normalize_url("https://example.com/") == "https://example.com"
    assert normalize_url("https://example.com") == "https://example.com"
    assert (
        normalize_url("https://example.com/?q=test")
        == "https://example.com?q=test"
    )


def test_get_domain():
    assert get_domain("https://www.example.com/path") == "www.example.com"
    assert get_domain("http://example.com:8080") == "example.com:8080"
    assert get_domain("https://EXAMPLE.COM") == "example.com"


def test_is_same_domain():
    allowed = get_domain("https://www.example.com")
    assert is_same_domain("https://www.example.com/about", allowed) is True
    assert is_same_domain("https://sub.example.com", allowed) is False
    assert (
        is_same_domain("https://example.com", allowed) is False
    )  # different subdomain
    assert (
        is_same_domain("https://WWW.EXAMPLE.COM", allowed) is True
    )  # case insensitive


def test_resolve_links():
    base = "https://example.com/blog/"
    links = {
        "/about",  # relative root
        "contact.html",  # relative current dir
        "./team",  # current dir
        "../services",  # parent dir
        "https://example.com/news",  # absolute same domain
    }

    resolved = resolve_links(base, links)

    expected = {
        "https://example.com/about",
        "https://example.com/blog/contact.html",
        "https://example.com/blog/team",
        "https://example.com/services",
        "https://example.com/news",
    }

    assert resolved == expected
