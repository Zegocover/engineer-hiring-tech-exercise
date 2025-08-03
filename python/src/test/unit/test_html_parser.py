from urlcrawler import HtmlParser

parser = HtmlParser()
main_url = "http://example.com"


# NOTE: Naming convention: test_{given}_{then}
# Even better: create individual test cases for each scenario.
def test_html_parser_valid_html_finds_valid_urls():
    # NOTE: Following the pattern of Define, Act, Assert
    response = """
    <html>
        <body>
            <a href="http://example.com/page1">Page 1</a>
            <a href="/page2">relative</a>
            <a href="example.com/page3">semi relative</a>
            <a href="">Empty</a>
            <a href="#">In Page</a>
            <a href="https://google.com">External</a>
            <a href="ftp://google.com/download.png">Download file</a>
            <a href="javascript:void(0)">Invalid Link</a>
            <a href="mailto:guillermo.molina@zego.com</a>
            <a href="tel:+1234567890">Call Us</a>
        </body>
    </html>
    """
    expected_links = [
        "http://example.com/page1",
        "http://example.com/page2",
        "http://example.com/page3",
        "https://google.com",
    ]
    # Act
    result = parser.find_urls(main_url, response)
    # Assert
    assert sorted(result) == sorted(
        expected_links
    ), f"Expected {expected_links}, but got {result}"


def test_html_parser_invalid_html_returns_empty_list():
    response = """
    {
        "html": "This is not valid HTML"
    }
    """
    # Act
    result = parser.find_urls(main_url, response)
    # Assert
    assert result == [], f"Expected empty list, but got {result}"
