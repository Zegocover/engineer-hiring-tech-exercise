from crawlspace._parser import Parser


def test_parser():
    parser = Parser()
    base_url: str = "http://localhost:8888"
    page: str = ""

    result = parser.parse(base_url, page)

    assert result == {"http://localhost:8888/empty-page"}
