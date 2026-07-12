import pytest

from crawler.src.filters import ExactDomainFilter


def test_allows_exact_hostname() -> None:
    domain_filter = ExactDomainFilter("https://example.com")
    assert domain_filter.is_allowed("https://example.com/page") is True


def test_rejects_www_subdomain_when_seed_is_bare() -> None:
    domain_filter = ExactDomainFilter("https://example.com")
    assert domain_filter.is_allowed("https://www.example.com/page") is False


def test_rejects_other_subdomain() -> None:
    domain_filter = ExactDomainFilter("https://example.com")
    assert domain_filter.is_allowed("https://blog.example.com/page") is False


def test_rejects_different_domain() -> None:
    domain_filter = ExactDomainFilter("https://example.com")
    assert domain_filter.is_allowed("https://other.com/page") is False


def test_allows_exact_www_when_seed_is_www() -> None:
    domain_filter = ExactDomainFilter("https://www.example.com")
    assert domain_filter.is_allowed("https://www.example.com/page") is True
    assert domain_filter.is_allowed("https://example.com/page") is False


def test_hostname_comparison_is_case_insensitive() -> None:
    domain_filter = ExactDomainFilter("https://EXAMPLE.com")
    assert domain_filter.is_allowed("https://example.com/page") is True


def test_raises_for_base_url_without_hostname() -> None:
    with pytest.raises(ValueError):
        ExactDomainFilter("not-a-url")
