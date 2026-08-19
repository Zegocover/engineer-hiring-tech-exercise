import pytest

from site_crawler.url_policy import UrlPolicy


def test_policy_allows_exact_host_and_removes_fragment() -> None:
    policy = UrlPolicy("https://example.test/start")

    assert policy.normalize(
        "https://example.test/docs#intro"
    ) == "https://example.test/docs"


def test_policy_rejects_other_hosts_and_subdomains() -> None:
    policy = UrlPolicy("https://example.test")

    assert policy.normalize("https://www.example.test/docs") is None
    assert policy.normalize("https://other.test/docs") is None


def test_policy_requires_http_url_with_hostname() -> None:
    with pytest.raises(ValueError):
        UrlPolicy("file:///tmp/index.html")
