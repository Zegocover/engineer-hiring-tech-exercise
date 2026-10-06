from site_crawler.parser import extract_links


PAGE = """
<html><body>
  <a href="/about">About</a>
  <a href="https://example.com/about#team">dup</a>
  <a href="https://blog.example.com/post">subdomain</a>
  <a href="https://other.test/x">off site</a>
  <a href="mailto:hi@example.com">mail</a>
</body></html>
"""


def test_extracts_unique_absolute_links_and_skips_mailto():
    links = extract_links(PAGE, "https://example.com/")
    assert links == [
        "https://example.com/about",
        "https://blog.example.com/post",
        "https://other.test/x",
    ]


def test_skips_fragments_javascript_and_empty_hrefs():
    html = """
    <a href="#section">frag</a>
    <a href="javascript:void(0)">js</a>
    <a href="tel:+440000">tel</a>
    <a href="">empty</a>
    <a href="docs/guide">relative</a>
    """
    assert extract_links(html, "https://example.com/a/") == [
        "https://example.com/a/docs/guide",
    ]
