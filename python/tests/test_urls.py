"""Tests for URL helper functions."""

import pytest

from crawler import urls


@pytest.mark.parametrize(
    ("referrer", "href", "expected"),
    [
        pytest.param(
            "https://example.com/dir/",
            "page",
            "https://example.com/dir/page",
            id="relative-path",
        ),
        pytest.param(
            "https://example.com/dir/",
            "subdir/",
            "https://example.com/dir/subdir/",
            id="relative-path-keeps-trailing-slash",
        ),
        pytest.param(
            "https://example.com/dir/",
            "https://other.com/x",
            "https://other.com/x",
            id="absolute-url",
        ),
        pytest.param(
            "https://example.com/dir/",
            "//cdn.example.com/asset",
            "https://cdn.example.com/asset",
            id="scheme-relative",
        ),
    ],
)
def test_resolve_url(referrer: str, href: str, expected: str) -> None:
    assert urls.resolve_url(referrer, href) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        pytest.param(
            "https://example.com/path#section",
            "https://example.com/path",
            id="strips-fragment",
        ),
        pytest.param(
            "https://example.com/path",
            "https://example.com/path",
            id="no-fragment",
        ),
    ],
)
def test_strip_fragment(url: str, expected: str) -> None:
    assert urls.strip_fragment(url) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        pytest.param(
            "HTTP://Example.COM:80/path?x=1#frag",
            "http://example.com/path?x=1#frag",
            id="lowercase-and-strip-default-port",
        ),
        pytest.param(
            "https://example.com/Path/With/Case",
            "https://example.com/Path/With/Case",
            id="preserves-path-case",
        ),
        pytest.param(
            "https://example.com/path/",
            "https://example.com/path",
            id="strips-trailing-slash",
        ),
        pytest.param(
            "https://example.com:8443/path",
            "https://example.com:8443/path",
            id="keep-non-default-port",
        ),
    ],
)
def test_normalise_for_dedupe(url: str, expected: str) -> None:
    assert urls.normalise_for_dedupe(url) == expected


@pytest.mark.parametrize(
    ("url", "expected", "error"),
    [
        pytest.param(
            "https://example.com",
            True,
            None,
            id="https-url",
        ),
        pytest.param(
            "http://example.com",
            True,
            None,
            id="http-url",
        ),
        pytest.param(
            "mailto:hello@example.com",
            False,
            None,
            id="non-supported-scheme",
        ),
        pytest.param(
            "/relative/path",
            None,
            urls.UrlParsingError,
            id="missing-scheme-raises",
        ),
    ],
)
def test_is_supported_scheme(url: str, expected: bool, error) -> None:
    if error is not None:
        with pytest.raises(error):
            urls.is_supported_scheme(url)
    else:
        assert urls.is_supported_scheme(url) is expected


@pytest.mark.parametrize(
    ("url", "base_url", "expected", "error"),
    [
        pytest.param(
            "https://sub.example.com/page",
            "https://example.com",
            False,
            None,
            id="subdomain-not-in-scope",
        ),
        pytest.param(
            "https://example.org/page",
            "https://example.com",
            False,
            None,
            id="different-domain",
        ),
        pytest.param(
            "http://localhost/page",
            "http://localhost",
            True,
            None,
            id="localhost-in-scope",
        ),
    ],
)
def test_is_domain_in_scope(
    url: str, base_url: str, expected: bool, error
) -> None:
    if error is not None:
        with pytest.raises(error):
            urls.is_domain_in_scope(url, base_url)
    else:
        assert urls.is_domain_in_scope(url, base_url) is expected
