from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from site_crawler.fetchers import DefaultHttpxFetcher
from site_crawler.models import FetchError

URL = "https://example.com/"
HTML = {"content-type": "text/html; charset=utf-8"}


@pytest.fixture
async def fetcher() -> AsyncIterator[DefaultHttpxFetcher]:
    f = DefaultHttpxFetcher(backoff=0, max_retries=2)
    yield f
    await f.aclose()


@respx.mock
async def test_success(fetcher: DefaultHttpxFetcher) -> None:
    respx.get(URL).respond(200, headers=HTML, text="<a href='/x'>x</a>")
    result = await fetcher.fetch(URL)
    assert result.status == 200
    assert result.final_url == URL
    assert result.is_html
    assert b"/x" in result.body


@respx.mock
async def test_redirect_sets_final_url(fetcher: DefaultHttpxFetcher) -> None:
    respx.get("https://example.com/old").respond(301, headers={"location": "/new/"})
    respx.get("https://example.com/new/").respond(200, headers=HTML, text="")
    result = await fetcher.fetch("https://example.com/old")
    assert result.url == "https://example.com/old"
    assert result.final_url == "https://example.com/new/"


@respx.mock
async def test_transient_503_then_200_recovers(fetcher: DefaultHttpxFetcher) -> None:
    route = respx.get(URL)
    route.side_effect = [httpx.Response(503), httpx.Response(200, headers=HTML, text="ok")]
    result = await fetcher.fetch(URL)
    assert result.status == 200
    assert route.call_count == 2


@respx.mock
async def test_retry_after_honoured(fetcher: DefaultHttpxFetcher) -> None:
    route = respx.get(URL)
    route.side_effect = [
        httpx.Response(429, headers={"retry-after": "0"}),
        httpx.Response(200, headers=HTML, text=""),
    ]
    assert (await fetcher.fetch(URL)).status == 200


@respx.mock
async def test_persistent_500_raises_fetch_error(fetcher: DefaultHttpxFetcher) -> None:
    route = respx.get(URL).respond(500)
    with pytest.raises(FetchError, match="HTTP 500"):
        await fetcher.fetch(URL)
    assert route.call_count == 3  # first try + 2 retries


@respx.mock
async def test_404_not_retried(fetcher: DefaultHttpxFetcher) -> None:
    route = respx.get(URL).respond(404)
    with pytest.raises(FetchError, match="HTTP 404"):
        await fetcher.fetch(URL)
    assert route.call_count == 1


@respx.mock
async def test_timeout_retried_then_raises(fetcher: DefaultHttpxFetcher) -> None:
    route = respx.get(URL).mock(side_effect=httpx.ConnectTimeout("slow"))
    with pytest.raises(FetchError, match="ConnectTimeout"):
        await fetcher.fetch(URL)
    assert route.call_count == 3


@respx.mock
async def test_non_html_body_not_downloaded(fetcher: DefaultHttpxFetcher) -> None:
    respx.get(URL).respond(200, headers={"content-type": "application/pdf"}, content=b"%PDF")
    result = await fetcher.fetch(URL)
    assert not result.is_html
    assert result.body == b""


@respx.mock
async def test_body_capped() -> None:
    fetcher = DefaultHttpxFetcher(max_body_bytes=10)
    respx.get(URL).respond(200, headers=HTML, content=b"x" * 100)
    try:
        assert len((await fetcher.fetch(URL)).body) == 10
    finally:
        await fetcher.aclose()


@respx.mock
async def test_text_plain_body_downloaded(fetcher: DefaultHttpxFetcher) -> None:
    respx.get("https://example.com/robots.txt").respond(
        200, headers={"content-type": "text/plain"}, text="User-agent: *\nDisallow: /x/\n"
    )
    result = await fetcher.fetch("https://example.com/robots.txt")
    assert b"Disallow" in result.body
