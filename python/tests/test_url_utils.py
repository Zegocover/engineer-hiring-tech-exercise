"""Unit tests for url_utils module."""


from crawler.url_utils import (
    extract_domain,
    is_same_domain,
    is_valid_http_url,
    normalize_url,
    should_skip_url,
)


class TestExtractDomain:
    """Tests for extract_domain function."""

    def test_simple_domain(self) -> None:
        assert extract_domain("https://example.com/path") == "example.com"

    def test_domain_with_port(self) -> None:
        assert extract_domain("https://example.com:8080/path") == "example.com:8080"

    def test_uppercase_domain(self) -> None:
        assert extract_domain("https://EXAMPLE.COM/path") == "example.com"

    def test_subdomain(self) -> None:
        assert extract_domain("https://www.example.com/path") == "www.example.com"

    def test_empty_url(self) -> None:
        assert extract_domain("") == ""


class TestNormalizeUrl:
    """Tests for normalize_url function."""

    def test_removes_fragment(self) -> None:
        result = normalize_url("https://example.com/page#section")
        assert result == "https://example.com/page"

    def test_removes_trailing_slash(self) -> None:
        result = normalize_url("https://example.com/page/")
        assert result == "https://example.com/page"

    def test_preserves_root_slash(self) -> None:
        result = normalize_url("https://example.com/")
        assert result == "https://example.com/"

    def test_adds_root_slash_when_missing(self) -> None:
        result = normalize_url("https://example.com")
        assert result == "https://example.com/"

    def test_lowercases_scheme_and_host(self) -> None:
        result = normalize_url("HTTPS://EXAMPLE.COM/Path")
        assert result == "https://example.com/Path"

    def test_resolves_relative_url(self) -> None:
        result = normalize_url("/about", "https://example.com/page")
        assert result == "https://example.com/about"

    def test_resolves_relative_url_with_dot(self) -> None:
        result = normalize_url("./contact", "https://example.com/pages/about")
        assert result == "https://example.com/pages/contact"

    def test_preserves_query_string(self) -> None:
        result = normalize_url("https://example.com/search?q=test")
        assert result == "https://example.com/search?q=test"

    def test_absolute_url_ignores_base(self) -> None:
        result = normalize_url("https://other.com/page", "https://example.com")
        assert result == "https://other.com/page"


class TestIsSameDomain:
    """Tests for is_same_domain function."""

    def test_same_domain_returns_true(self) -> None:
        assert is_same_domain("https://example.com/page", "example.com") is True

    def test_different_domain_returns_false(self) -> None:
        assert is_same_domain("https://other.com/page", "example.com") is False

    def test_subdomain_returns_false(self) -> None:
        # Strict matching - subdomains are different
        assert is_same_domain("https://www.example.com/page", "example.com") is False

    def test_case_insensitive(self) -> None:
        assert is_same_domain("https://EXAMPLE.COM/page", "example.com") is True
        assert is_same_domain("https://example.com/page", "EXAMPLE.COM") is True

    def test_with_port(self) -> None:
        assert is_same_domain("https://example.com:8080/page", "example.com:8080") is True
        assert is_same_domain("https://example.com:8080/page", "example.com") is False


class TestShouldSkipUrl:
    """Tests for should_skip_url function."""

    def test_empty_url(self) -> None:
        assert should_skip_url("") is True
        assert should_skip_url("   ") is True

    def test_mailto_link(self) -> None:
        assert should_skip_url("mailto:test@example.com") is True

    def test_javascript_link(self) -> None:
        assert should_skip_url("javascript:void(0)") is True

    def test_tel_link(self) -> None:
        assert should_skip_url("tel:+1234567890") is True

    def test_pdf_file(self) -> None:
        assert should_skip_url("https://example.com/doc.pdf") is True
        assert should_skip_url("https://example.com/doc.PDF") is True

    def test_image_files(self) -> None:
        assert should_skip_url("https://example.com/image.jpg") is True
        assert should_skip_url("https://example.com/image.png") is True
        assert should_skip_url("https://example.com/image.gif") is True

    def test_archive_files(self) -> None:
        assert should_skip_url("https://example.com/file.zip") is True
        assert should_skip_url("https://example.com/file.tar.gz") is True

    def test_valid_html_page(self) -> None:
        assert should_skip_url("https://example.com/page") is False
        assert should_skip_url("https://example.com/page.html") is False

    def test_relative_url(self) -> None:
        # Relative URLs should not be skipped (they'll be resolved later)
        assert should_skip_url("/about") is False


class TestIsValidHttpUrl:
    """Tests for is_valid_http_url function."""

    def test_https_url(self) -> None:
        assert is_valid_http_url("https://example.com") is True

    def test_http_url(self) -> None:
        assert is_valid_http_url("http://example.com") is True

    def test_relative_url(self) -> None:
        assert is_valid_http_url("/relative/path") is False

    def test_mailto_url(self) -> None:
        assert is_valid_http_url("mailto:test@example.com") is False

    def test_empty_url(self) -> None:
        assert is_valid_http_url("") is False
