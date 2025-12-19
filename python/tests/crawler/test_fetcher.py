# tests/test_fetcher.py
import pytest
import responses
from crawler.fetcher import fetch_url


@responses.activate
def test_fetch_url_success():
    url = "https://httpbin.org/html"
    responses.add(responses.GET, url, body="<html><body>Test</body></html>", status=200)

    result_url, html = fetch_url(url)
    assert result_url == url
    assert html is not None
    assert "<body>Test</body>" in html


@responses.activate
def test_fetch_url_404():
    url = "https://httpbin.org/status/404"
    responses.add(responses.GET, url, status=404)

    result_url, html = fetch_url(url)
    assert result_url == url
    assert html is None


@responses.activate
def test_fetch_url_redirect():
    final_url = "https://httpbin.org/redirected"
    responses.add(responses.GET, "https://httpbin.org/redirect/1", status=302,
                  headers={"Location": final_url})
    responses.add(responses.GET, final_url, body="<html>Final</html>", status=200)

    result_url, html = fetch_url("https://httpbin.org/redirect/1")
    assert result_url == "https://httpbin.org/redirect/1"  # original URL preserved
    assert html is not None
    assert "Final" in html