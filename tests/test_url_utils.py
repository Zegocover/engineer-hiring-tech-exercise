from site_crawler.url_utils import canonical_url, same_site


def test_strips_fragment_and_lowercases_host():
    assert canonical_url("https://Example.com/a#section") == "https://example.com/a"


def test_resolves_relative_link():
    assert canonical_url("/b", "https://example.com/a") == "https://example.com/b"


def test_rejects_non_http():
    assert canonical_url("mailto:a@example.com") is None
    assert canonical_url("javascript:void(0)", "https://example.com") is None


def test_subdomain_is_not_the_same_site():
    assert same_site("https://example.com/a", "example.com")
    assert not same_site("https://blog.example.com/a", "example.com")
    assert not same_site("https://other.com/", "example.com")
