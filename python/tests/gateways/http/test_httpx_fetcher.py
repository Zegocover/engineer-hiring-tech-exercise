import httpx
from pytest_httpx import HTTPXMock

from domains.crawler.ports import Fetcher
from gateways.http.httpx_fetcher import HttpxFetcher


async def test_satisfies_the_port() -> None:
    async with httpx.AsyncClient() as client:
        assert isinstance(HttpxFetcher(client), Fetcher)


async def test_fetches_html_200(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="http://a.com/p",
        html="<html><a href='/x'>x</a></html>",
        headers={"content-type": "text/html; charset=utf-8"},
    )
    async with httpx.AsyncClient() as client:
        result = await HttpxFetcher(client).fetch("http://a.com/p")
    assert result.status == 200
    assert result.content_type is not None and result.content_type.startswith("text/html")
    assert result.html is not None and "href" in result.html
    assert result.error is None


async def test_non_html_returns_no_body(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="http://a.com/file.pdf",
        content=b"%PDF-1.4 ...",
        headers={"content-type": "application/pdf"},
    )
    async with httpx.AsyncClient() as client:
        result = await HttpxFetcher(client).fetch("http://a.com/file.pdf")
    assert result.status == 200
    assert result.html is None
    assert result.error is None


async def test_records_final_url_after_redirect(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="http://a.com/old",
        status_code=301,
        headers={"location": "http://a.com/new"},
    )
    httpx_mock.add_response(
        url="http://a.com/new",
        html="<html></html>",
        headers={"content-type": "text/html"},
    )
    async with httpx.AsyncClient() as client:
        result = await HttpxFetcher(client).fetch("http://a.com/old")
    assert result.requested_url == "http://a.com/old"
    assert result.final_url == "http://a.com/new"
    assert result.status == 200


async def test_http_error_status_is_captured(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="http://a.com/missing", status_code=404)
    async with httpx.AsyncClient() as client:
        result = await HttpxFetcher(client).fetch("http://a.com/missing")
    assert result.status == 404
    assert result.html is None


async def test_network_error_becomes_error_result(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.ConnectTimeout("boom"), url="http://a.com/slow")
    async with httpx.AsyncClient() as client:
        result = await HttpxFetcher(client).fetch("http://a.com/slow")
    assert result.status is None
    assert result.html is None
    assert result.error is not None


async def test_uppercase_content_type_is_treated_as_html(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="http://a.com/p",
        html="<html><a href='/x'>x</a></html>",
        headers={"content-type": "Text/HTML; charset=utf-8"},
    )
    async with httpx.AsyncClient() as client:
        result = await HttpxFetcher(client).fetch("http://a.com/p")
    assert result.html is not None
    assert result.content_type == "Text/HTML; charset=utf-8"  # original casing preserved


async def test_oversized_body_is_dropped(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="http://a.com/big",
        html="<html>" + "x" * 100 + "</html>",
        headers={"content-type": "text/html"},
    )
    async with httpx.AsyncClient() as client:
        result = await HttpxFetcher(client, max_bytes=10).fetch("http://a.com/big")
    assert result.status == 200
    assert result.html is None
