from __future__ import annotations

import httpx
from pytest_httpx import HTTPXMock

from crawler.web.fetch import FetchError, FetchOk, FetchResult, fetch_html, fetch_robots

URL = "http://h/p"
ROBOTS = "http://h/robots.txt"


async def _fetch_html(url: str) -> FetchResult:
    async with httpx.AsyncClient() as client:
        return await fetch_html(client, url)


async def test_html_ok(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=URL, headers={"content-type": "text/html"}, content=b"<a href='x'>hi</a>"
    )
    result = await _fetch_html(URL)
    assert isinstance(result, FetchOk)
    assert b"href" in result.body


async def test_non_html_is_skipped(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=URL, headers={"content-type": "application/json"}, content=b"{}")
    assert await _fetch_html(URL) == FetchError("non_html", "application/json")


async def test_non_2xx_is_status_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=URL, status_code=404)
    assert await _fetch_html(URL) == FetchError("status", "404")


async def test_redirect_is_not_followed(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=URL, status_code=302, headers={"location": "http://h/elsewhere"})
    assert await _fetch_html(URL) == FetchError("status", "302")


async def test_timeout(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.ReadTimeout("slow"))
    result = await _fetch_html(URL)
    assert isinstance(result, FetchError)
    assert result.kind == "timeout"


async def test_transport_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.ConnectError("boom"))
    result = await _fetch_html(URL)
    assert isinstance(result, FetchError)
    assert result.kind == "transport"


async def test_fetch_robots_returns_text(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=ROBOTS, text="User-agent: *\nDisallow: /x")
    async with httpx.AsyncClient() as client:
        text = await fetch_robots(client, ROBOTS)
    assert text is not None
    assert "Disallow" in text


async def test_fetch_robots_missing_is_none(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=ROBOTS, status_code=404)
    async with httpx.AsyncClient() as client:
        assert await fetch_robots(client, ROBOTS) is None
