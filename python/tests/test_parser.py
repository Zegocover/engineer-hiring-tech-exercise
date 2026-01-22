import pytest
from src.parser import extract_links

def test_extract_links():
    html = """
    <html>
        <body>
            <a href="/page1">Page 1</a>
            <a href="https://example.com/page2">Page 2</a>
            <a href="https://google.com">External</a>
            <a href="mailto:test@example.com">Email</a>
        </body>
    </html>
    """
    base_url = "https://example.com"
    links = extract_links(html, base_url)
    
    expected = {
        "https://example.com/page1",
        "https://example.com/page2"
    }
    assert links == expected

def test_extract_links_empty():
    html = "<html></html>"
    base_url = "https://example.com"
    assert extract_links(html, base_url) == set()
