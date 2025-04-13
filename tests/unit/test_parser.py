from crawlspace._parser import Parser


def test_parser(html):
    parser = Parser()
    base_url: str = "http://localhost:8888"
    page: str = html.get("parse_test.html")

    result = parser.parse(base_url, page)

    assert result == {"http://localhost:8888/empty_page.html"}
