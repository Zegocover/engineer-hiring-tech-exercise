import pytest

from domains.crawler.urls import extract_host, normalize, same_host


class TestNormalize:
    def test_strips_fragment(self) -> None:
        assert normalize("http://a.com/p#section", "http://a.com/") == "http://a.com/p"

    def test_lowercases_host_only(self) -> None:
        assert normalize("http://A.COM/Path", "http://a.com/") == "http://a.com/Path"

    def test_drops_default_http_port(self) -> None:
        assert normalize("http://a.com:80/p", "http://a.com/") == "http://a.com/p"

    def test_drops_default_https_port(self) -> None:
        assert normalize("https://a.com:443/p", "https://a.com/") == "https://a.com/p"

    def test_keeps_nondefault_port(self) -> None:
        assert normalize("http://a.com:8080/p", "http://a.com/") == "http://a.com:8080/p"

    def test_resolves_relative_path(self) -> None:
        assert normalize("../x", "http://a.com/dir/page") == "http://a.com/x"

    def test_resolves_absolute_path(self) -> None:
        assert normalize("/x", "http://a.com/dir/page") == "http://a.com/x"

    def test_resolves_protocol_relative(self) -> None:
        assert normalize("//b.com/x", "https://a.com/") == "https://b.com/x"

    def test_preserves_query_string(self) -> None:
        assert normalize("/p?b=2&a=1", "http://a.com/") == "http://a.com/p?b=2&a=1"

    def test_empty_path_becomes_root(self) -> None:
        assert normalize("http://a.com", "http://a.com/") == "http://a.com/"

    @pytest.mark.parametrize(
        "href",
        ["mailto:x@a.com", "tel:+123", "javascript:void(0)", "data:text/plain,hi", "#frag"],
    )
    def test_non_navigable_returns_none(self, href: str) -> None:
        assert normalize(href, "http://a.com/") is None


class TestExtractHost:
    def test_lowercases(self) -> None:
        assert extract_host("http://A.com/p") == "a.com"

    def test_drops_default_port(self) -> None:
        assert extract_host("http://a.com:80/p") == "a.com"

    def test_keeps_nondefault_port(self) -> None:
        assert extract_host("http://a.com:8080/p") == "a.com:8080"


class TestSameHost:
    def test_identical(self) -> None:
        assert same_host("http://a.com/x", "a.com") is True

    def test_case_insensitive(self) -> None:
        assert same_host("http://A.COM/x", "a.com") is True

    def test_subdomain_is_different(self) -> None:
        assert same_host("http://www.a.com/x", "a.com") is False

    def test_other_domain(self) -> None:
        assert same_host("http://b.com/x", "a.com") is False
