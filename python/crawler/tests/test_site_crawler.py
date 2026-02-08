from __future__ import annotations

import pytest

from crawler.site_crawler import SiteCrawler


def test_site_crawler_accepts_valid_defaults() -> None:
    crawler = SiteCrawler("https://example.com")
    assert crawler.batch_size == 10
    assert crawler.max_urls is None
    assert crawler.timeout == 10.0
    assert crawler.retries == 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"batch_size": 0},
        {"batch_size": 11},
        {"max_urls": 0},
        {"max_urls": 1001},
        {"timeout": -0.1},
        {"timeout": 10.1},
        {"retries": -1},
        {"retries": 4},
    ],
)

def test_site_crawler_rejects_invalid_bounds(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        SiteCrawler("https://example.com", **kwargs)
