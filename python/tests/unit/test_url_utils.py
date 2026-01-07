"""Tests for URL utilities."""

import pytest

from crawler.url_utils import get_base_domain, process_url


def test_get_base_domain_strips_www() -> None:
    assert get_base_domain("https://www.example.com") == "example.com"


@pytest.mark.parametrize(
    ("href", "expected"),
    [
        ("/about", "https://example.com/about"),
        ("/page#section", "https://example.com/page"),
        ("/about/", "https://example.com/about"),
        ("https://www.example.com/other", "https://example.com/other"),
        ("https://other.com/page", None),
        ("https://blog.example.com/page", None),
        ("mailto:test@example.com", None),
    ],
)
def test_process_url(href: str, expected: str | None) -> None:
    result = process_url(href, "https://example.com/page", "example.com")
    assert result == expected