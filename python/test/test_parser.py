import sys
import os
# Add parent directory to sys.path so we can import classes from the main codebase
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import pytest
from core.link_parser import LinkParser

class TestLinkParser:
    @pytest.fixture
    def parser(self):
        return LinkParser(domain="example.com")

    def test_extract_same_domain_links(self, parser):
        html = """
        <html>
        <body>
            <a href="http://example.com/page1">Page 1</a>
            <a href="http://example.com/page2">Page 2</a>
            <a href="http://other.com/page">Other</a>
        </body>
        </html>
        """
        current_url = "http://example.com"
        
        links = parser.extract_links(html, current_url)
        
        assert "http://example.com/page1" in links
        assert "http://example.com/page2" in links
        assert "http://other.com/page" not in links

    def test_convert_relative_links(self, parser):
        html = """
        <html>
        <body>
            <a href="/relative">Relative</a>
            <a href="page.html">Page</a>
        </body>
        </html>
        """
        current_url = "http://example.com/folder/"
        
        links = parser.extract_links(html, current_url)
        
        assert "http://example.com/relative" in links
        assert "http://example.com/folder/page.html" in links

    def test_remove_fragments(self, parser):
        html = """
        <html>
        <body>
            <a href="http://example.com/page#section1">Page Section 1</a>
            <a href="http://example.com/page#section2">Page Section 2</a>
        </body>
        </html>
        """
        current_url = "http://example.com"
        
        links = parser.extract_links(html, current_url)
        
        # Both should resolve to the same URL without fragments
        assert links.count("http://example.com/page") == 1

    def test_ignore_empty_href(self, parser):
        html = """
        <html>
        <body>
            <a href="">Empty</a>
            <a href="   ">Whitespace</a>
            <a href="http://example.com/valid">Valid</a>
        </body>
        </html>
        """
        current_url = "http://example.com"
        
        links = parser.extract_links(html, current_url)
        
        assert len(links) == 1
        assert "http://example.com/valid" in links

    def test_remove_duplicates(self, parser):
        html = """
        <html>
        <body>
            <a href="http://example.com/page">Page 1</a>
            <a href="http://example.com/page">Page 2</a>
            <a href="http://example.com/page">Page 3</a>
        </body>
        </html>
        """
        current_url = "http://example.com"
        
        links = parser.extract_links(html, current_url)
        
        assert len(links) == 1
        assert "http://example.com/page" in links

    def test_no_links_in_html(self, parser):
        html = """
        <html>
        <body>
            <p>No links here</p>
        </body>
        </html>
        """
        current_url = "http://example.com"
        
        links = parser.extract_links(html, current_url)
        
        assert len(links) == 0

    def test_links_without_href_ignored(self, parser):
        html = """
        <html>
        <body>
            <a>No href</a>
            <a name="anchor">Named anchor</a>
            <a href="http://example.com/valid">Valid</a>
        </body>
        </html>
        """
        current_url = "http://example.com"
        
        links = parser.extract_links(html, current_url)
        
        assert len(links) == 1
        assert "http://example.com/valid" in links