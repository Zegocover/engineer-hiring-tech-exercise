"""Unit tests for parser module."""


from crawler.parser import extract_links, is_html_content_type


class TestExtractLinks:
    """Tests for extract_links function."""

    def test_extracts_absolute_links(self) -> None:
        html = '<a href="https://example.com/page">Link</a>'
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_resolves_relative_links(self) -> None:
        html = '<a href="/about">About</a>'
        links = extract_links(html, "https://example.com/page")
        assert links == ["https://example.com/about"]

    def test_resolves_relative_dot_links(self) -> None:
        html = '<a href="./contact">Contact</a>'
        links = extract_links(html, "https://example.com/pages/about")
        assert links == ["https://example.com/pages/contact"]

    def test_extracts_multiple_links(self) -> None:
        html = """
        <a href="/page1">Page 1</a>
        <a href="/page2">Page 2</a>
        <a href="/page3">Page 3</a>
        """
        links = extract_links(html, "https://example.com")
        assert links == [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]

    def test_removes_duplicates(self) -> None:
        html = """
        <a href="/page">First</a>
        <a href="/page">Second</a>
        <a href="/page">Third</a>
        """
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_skips_mailto_links(self) -> None:
        html = """
        <a href="/page">Page</a>
        <a href="mailto:test@example.com">Email</a>
        """
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_skips_javascript_links(self) -> None:
        html = """
        <a href="/page">Page</a>
        <a href="javascript:void(0)">JS Link</a>
        """
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_skips_tel_links(self) -> None:
        html = """
        <a href="/page">Page</a>
        <a href="tel:+1234567890">Phone</a>
        """
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_skips_pdf_files(self) -> None:
        html = """
        <a href="/page">Page</a>
        <a href="/document.pdf">PDF</a>
        """
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_skips_image_files(self) -> None:
        html = """
        <a href="/page">Page</a>
        <a href="/image.jpg">Image</a>
        <a href="/photo.png">Photo</a>
        """
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_skips_empty_href(self) -> None:
        html = """
        <a href="">Empty</a>
        <a href="   ">Whitespace</a>
        <a href="/page">Page</a>
        """
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_handles_anchor_without_href(self) -> None:
        html = """
        <a name="section">Section</a>
        <a href="/page">Page</a>
        """
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_normalizes_links(self) -> None:
        html = '<a href="/page/#section">Link with fragment</a>'
        links = extract_links(html, "https://example.com")
        # Fragment should be removed
        assert links == ["https://example.com/page"]

    def test_handles_empty_html(self) -> None:
        links = extract_links("", "https://example.com")
        assert links == []

    def test_handles_html_without_links(self) -> None:
        html = "<p>No links here</p>"
        links = extract_links(html, "https://example.com")
        assert links == []

    def test_handles_malformed_html(self) -> None:
        # lxml should handle this gracefully
        html = '<a href="/page">Unclosed tag<a href="/other">Other'
        links = extract_links(html, "https://example.com")
        assert "https://example.com/page" in links

    def test_preserves_query_strings(self) -> None:
        html = '<a href="/search?q=test&page=1">Search</a>'
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/search?q=test&page=1"]

    def test_handles_whitespace_in_href(self) -> None:
        html = '<a href="  /page  ">Link</a>'
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_external_links_included(self) -> None:
        # External links should be extracted but will be filtered by crawler
        html = '<a href="https://other.com/page">External</a>'
        links = extract_links(html, "https://example.com")
        assert links == ["https://other.com/page"]


class TestIsHtmlContentType:
    """Tests for is_html_content_type function."""

    def test_text_html(self) -> None:
        assert is_html_content_type("text/html") is True

    def test_text_html_with_charset(self) -> None:
        assert is_html_content_type("text/html; charset=utf-8") is True

    def test_xhtml(self) -> None:
        assert is_html_content_type("application/xhtml+xml") is True

    def test_uppercase(self) -> None:
        assert is_html_content_type("TEXT/HTML") is True

    def test_json(self) -> None:
        assert is_html_content_type("application/json") is False

    def test_plain_text(self) -> None:
        assert is_html_content_type("text/plain") is False

    def test_none(self) -> None:
        assert is_html_content_type(None) is False

    def test_empty_string(self) -> None:
        assert is_html_content_type("") is False
