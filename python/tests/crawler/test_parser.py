# tests/test_parser.py
from crawler.parser import extract_links
from crawler.url_utils import normalize_url

SAMPLE_HTML = """
<html>
<head><title>Test Page</title></head>
<body>
    <a href="/about">About</a>
    <a href="contact/">Contact</a>
    <a href="./team.html">Team</a>
    <a href="../pricing">Pricing</a>
    <a href="https://example.com/news">News</a>
    <a href="https://blog.example.com">External Blog</a>
    <a href="//google.com">Protocol Relative</a>
    <a href="mailto:hello@example.com">Email</a>
    <a href="javascript:alert('hi')">JS</a>
    <a href="#section1">Anchor</a>
    <a href="/duplicate">Duplicate</a>
    <a href="/duplicate">Duplicate</a>
</body>
</html>
"""


def test_extract_links():
    base_url = "https://example.com/products/"
    allowed_domain = "example.com"

    links = extract_links(SAMPLE_HTML, base_url, allowed_domain)

    expected = {
        normalize_url("https://example.com/about"),
        normalize_url("https://example.com/products/contact"),
        normalize_url("https://example.com/products/team.html"),
        normalize_url("https://example.com/pricing"),
        normalize_url("https://example.com/news"),
        normalize_url("https://example.com/duplicate"),
    }

    assert links == expected
    assert len(links) == 6  # duplicates removed
    # External domains, non-http, anchors excluded
