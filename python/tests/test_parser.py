"""Unit tests for the URL parser module."""


from crawler.parser import (
    extract_links,
    get_domain,
    is_same_domain,
    is_valid_scheme,
    normalise_url,
)


class TestNormaliseUrl:
    """Tests for URL normalisation."""

    def test_removes_fragment(self):
        assert normalise_url("https://example.com/page#section") == "https://example.com/page"

    def test_removes_trailing_slash(self):
        assert normalise_url("https://example.com/page/") == "https://example.com/page"

    def test_preserves_root_path(self):
        assert normalise_url("https://example.com/") == "https://example.com/"
        assert normalise_url("https://example.com") == "https://example.com/"

    def test_lowercases_scheme_and_host(self):
        assert normalise_url("HTTPS://Example.COM/Page") == "https://example.com/Page"

    def test_preserves_query_string(self):
        assert normalise_url("https://example.com/s?q=test") == "https://example.com/s?q=test"

    def test_preserves_port(self):
        assert normalise_url("https://example.com:8080/path") == "https://example.com:8080/path"


class TestGetDomain:
    """Tests for domain extraction."""

    def test_simple_domain(self):
        assert get_domain("https://example.com/page") == "example.com"

    def test_domain_with_port(self):
        assert get_domain("https://example.com:8080/page") == "example.com:8080"

    def test_subdomain(self):
        assert get_domain("https://www.example.com/page") == "www.example.com"

    def test_lowercases(self):
        assert get_domain("https://Example.COM/page") == "example.com"


class TestIsSameDomain:
    """Tests for domain comparison."""

    def test_same_domain(self):
        assert is_same_domain("https://example.com/page", "example.com") is True

    def test_different_domain(self):
        assert is_same_domain("https://other.com/page", "example.com") is False

    def test_subdomain_is_different(self):
        assert is_same_domain("https://www.example.com/page", "example.com") is False
        assert is_same_domain("https://sub.example.com/page", "example.com") is False

    def test_different_port_is_different(self):
        assert is_same_domain("https://example.com:8080/page", "example.com") is False


class TestIsValidScheme:
    """Tests for scheme validation."""

    def test_http(self):
        assert is_valid_scheme("http://example.com") is True

    def test_https(self):
        assert is_valid_scheme("https://example.com") is True

    def test_ftp_invalid(self):
        assert is_valid_scheme("ftp://example.com") is False

    def test_mailto_invalid(self):
        assert is_valid_scheme("mailto:user@example.com") is False


class TestExtractLinks:
    """Tests for link extraction from HTML."""

    def test_extracts_internal_links(self, sample_html, base_url, base_domain):
        internal, _ = extract_links(sample_html, base_url, base_domain)

        assert "https://example.com/about" in internal
        assert "https://example.com/contact" in internal
        assert "https://example.com/products" in internal
        assert "https://example.com/relative/path" in internal

    def test_excludes_external_from_internal(self, sample_html, base_url, base_domain):
        internal, _ = extract_links(sample_html, base_url, base_domain)

        assert "https://other.com/external" not in internal

    def test_excludes_subdomains_from_internal(self, sample_html, base_url, base_domain):
        internal, _ = extract_links(sample_html, base_url, base_domain)

        assert all("sub.example.com" not in link for link in internal)

    def test_all_links_includes_external(self, sample_html, base_url, base_domain):
        _, all_links = extract_links(sample_html, base_url, base_domain)

        assert "https://other.com/external" in all_links
        assert "https://sub.example.com/subdomain" in all_links

    def test_excludes_non_http_schemes(self, sample_html, base_url, base_domain):
        internal, all_links = extract_links(sample_html, base_url, base_domain)

        # No mailto, tel, javascript, ftp links
        for link_set in (internal, all_links):
            for link in link_set:
                assert link.startswith(("http://", "https://"))

    def test_skips_empty_and_anchor_hrefs(self, sample_html, base_url, base_domain):
        internal, all_links = extract_links(sample_html, base_url, base_domain)

        # The #section anchor-only link should not appear
        assert not any(link.endswith("#section") for link in all_links)

    def test_normalises_fragments_away(self, sample_html, base_url, base_domain):
        internal, _ = extract_links(sample_html, base_url, base_domain)

        # https://example.com/page#fragment should become https://example.com/page
        assert "https://example.com/page" in internal

    def test_normalises_trailing_slashes(self, sample_html, base_url, base_domain):
        internal, _ = extract_links(sample_html, base_url, base_domain)

        # /page/ should become /page
        assert "https://example.com/page" in internal
        assert "https://example.com/page/" not in internal

    def test_strips_whitespace_from_href(self, sample_html, base_url, base_domain):
        internal, _ = extract_links(sample_html, base_url, base_domain)

        assert "https://example.com/whitespace" in internal

    def test_empty_html(self, base_url, base_domain):
        internal, all_links = extract_links("", base_url, base_domain)
        assert internal == set()
        assert all_links == set()

    def test_no_anchors(self, base_url, base_domain):
        html = "<html><body><p>No links here</p></body></html>"
        internal, all_links = extract_links(html, base_url, base_domain)
        assert internal == set()
        assert all_links == set()

    def test_relative_resolution(self):
        html = '<html><body><a href="../other">Link</a></body></html>'
        page_url = "https://example.com/dir/page"
        internal, _ = extract_links(html, page_url, "example.com")
        assert "https://example.com/other" in internal
