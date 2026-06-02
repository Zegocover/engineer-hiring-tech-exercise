from domains.crawler.extractor import SelectolaxExtractor


def test_extracts_anchor_area_and_link_hrefs() -> None:
    html = """
    <html><body>
      <a href="/a">a</a>
      <area href="/b">
      <link rel="canonical" href="/c">
      <a>no href</a>
    </body></html>
    """
    hrefs = SelectolaxExtractor().extract(html)
    assert set(hrefs) == {"/a", "/b", "/c"}


def test_handles_malformed_html() -> None:
    html = '<a href="/x">unclosed <a href="/y">'
    hrefs = SelectolaxExtractor().extract(html)
    assert "/x" in hrefs
    assert "/y" in hrefs


def test_resolves_against_base_href_when_present() -> None:
    html = '<head><base href="http://a.com/sub/"></head><body><a href="x">x</a></body>'
    hrefs = SelectolaxExtractor().extract(html)
    # With a <base>, the relative href resolves against the base.
    assert "http://a.com/sub/x" in hrefs


def test_empty_html_returns_empty_list() -> None:
    assert SelectolaxExtractor().extract("") == []
