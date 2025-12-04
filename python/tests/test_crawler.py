import pytest

from site_crawler.crawler import Crawler


@pytest.fixture
def crawler() -> Crawler:
    return Crawler()


@pytest.mark.parametrize(
    "base,url,expected",
    [
        ("https://example.com/", "https://example.com/path", True),
        ("https://example.com/", "https://sub.example.com/", False),
        ("https://example.com/", "https://example.co.uk/", False),
        ("https://Example.COM/", "https://EXAMPLE.com/SomePath", True),
        ("https://example.com/", "not-a-url", False),
        ("https://example.com/", "mailto:someone@example.com", False),
        ("not-a-valid-base", "https://example.com/", False),
    ],
)
def test_is_valid_parametrized(crawler: Crawler, base: str, url: str, expected: bool) -> None:
    assert crawler.is_valid(url, base) is expected

