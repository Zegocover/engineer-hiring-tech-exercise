from crawler.src.normaliser import DefaultURLNormaliser

normaliser = DefaultURLNormaliser()


def test_removes_fragment() -> None:
    assert normaliser.normalise_url("https://example.com/page#section", "https://example.com") == (
        "https://example.com/page"
    )


def test_resolves_relative_link() -> None:
    assert normaliser.normalise_url("/about", "https://example.com/blog/post") == "https://example.com/about"


def test_resolves_relative_link_against_current_page() -> None:
    assert normaliser.normalise_url("more", "https://example.com/blog/post") == "https://example.com/blog/more"


def test_lowercases_hostname_only() -> None:
    assert normaliser.normalise_url("https://EXAMPLE.com/Page", "https://example.com") == (
        "https://example.com/Page"
    )


def test_strips_default_http_port() -> None:
    assert normaliser.normalise_url("http://example.com:80/x", "http://example.com") == "http://example.com/x"


def test_strips_default_https_port() -> None:
    assert normaliser.normalise_url("https://example.com:443/x", "https://example.com") == "https://example.com/x"


def test_keeps_non_default_port() -> None:
    assert normaliser.normalise_url("https://example.com:8080/x", "https://example.com") == (
        "https://example.com:8080/x"
    )


def test_ignores_mailto_scheme() -> None:
    assert normaliser.normalise_url("mailto:someone@example.com", "https://example.com") is None


def test_ignores_javascript_scheme() -> None:
    assert normaliser.normalise_url("javascript:void(0)", "https://example.com") is None


def test_ignores_tel_scheme() -> None:
    assert normaliser.normalise_url("tel:+1234567890", "https://example.com") is None


def test_ignores_empty_href() -> None:
    assert normaliser.normalise_url("", "https://example.com") is None


def test_ignores_whitespace_only_href() -> None:
    assert normaliser.normalise_url("   ", "https://example.com") is None


def test_empty_path_canonicalizes_to_root() -> None:
    assert normaliser.normalise_url("https://example.com", "https://example.com") == "https://example.com/"


def test_query_params_sorted_for_dedup() -> None:
    first = normaliser.normalise_url("https://example.com/x?b=2&a=1", "https://example.com")
    second = normaliser.normalise_url("https://example.com/x?a=1&b=2", "https://example.com")
    assert first == second == "https://example.com/x?a=1&b=2"


def test_query_params_keep_blank_values() -> None:
    assert normaliser.normalise_url("https://example.com/x?flag=", "https://example.com") == (
        "https://example.com/x?flag="
    )


def test_query_params_duplicate_keys_sorted_stably() -> None:
    assert normaliser.normalise_url("https://example.com/x?a=3&a=1", "https://example.com") == (
        "https://example.com/x?a=1&a=3"
    )
