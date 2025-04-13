import pytest

from crawlspace._fetch_url_filter import FetchUrlFilter


def test_fetch_url_filter():
    base_url = "https://www.example.com"

    fetch_url_filter = FetchUrlFilter(base_url)

    result = fetch_url_filter.should_fetch("https://www.example.com/page")
    assert result == True


def test_will_not_visit_twice():
    base_url = "https://www.example.com"

    fetch_url_filter = FetchUrlFilter(base_url)

    fetch_url_filter.should_fetch("https://www.example.com/page")
    result = fetch_url_filter.should_fetch("https://www.example.com/page")

    assert result == False


def test_will_not_visit_external_sites():
    base_url = "https://www.example.com"

    fetch_url_filter = FetchUrlFilter(base_url)

    result = fetch_url_filter.should_fetch("https://another-page.com")

    assert result == False


def test_will_not_visit_other_subdomains():
    base_url = "https://www.example.com"

    fetch_url_filter = FetchUrlFilter(base_url)

    result = fetch_url_filter.should_fetch("https://spy.example.com")

    assert result == False


@pytest.mark.parametrize(
    "target_url, expected_result",
    [
        ("http://www.example.com/public", True),
        ("https://www.example.com/public", True),
        ("ftp://www.example.com/public", False),
    ],
)
def test_scheme_https_or_http_is_ok(target_url, expected_result):
    base_url = "https://www.example.com"

    fetch_url_filter = FetchUrlFilter(base_url)

    result = fetch_url_filter.should_fetch(target_url)

    assert result == expected_result


def test_fragments_count():
    base_url = "https://www.example.com"

    fetch_url_filter = FetchUrlFilter(base_url)

    fetch_url_filter.should_fetch("https://www.example.com/page")
    result = fetch_url_filter.should_fetch("https://www.example.com/page#mycooltitle")

    assert result == False
