"""Tests for HttpxFetcher, with all network traffic mocked via respx."""

from __future__ import annotations

import httpx
import pytest
import respx

from crawler.fetcher import HttpxFetcher

URL = "https://example.com/"


@respx.mock
async def test_fetch_html_success() -> None:
    respx.get(URL).mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=b"<html><a href='/x'>x</a></html>",
        )
    )
    async with HttpxFetcher() as fetcher:
        result = await fetcher.fetch(URL)

    assert result.ok
    assert result.status_code == 200
    assert result.final_url == URL
    assert result.content_type is not None and result.content_type.startswith("text/html")
    assert result.text is not None and "href" in result.text
    assert result.error is None


@respx.mock
async def test_non_html_body_is_not_downloaded() -> None:
    route = respx.get(URL).mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            content=b"%PDF-1.7 ...",
        )
    )
    async with HttpxFetcher() as fetcher:
        result = await fetcher.fetch(URL)

    assert route.called
    assert result.ok  # a 200 is still a successful fetch
    assert result.content_type == "application/pdf"
    assert result.text is None  # but we never parse it


@respx.mock
async def test_missing_content_type_is_treated_as_non_html() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, content=b"<html></html>"))
    async with HttpxFetcher() as fetcher:
        result = await fetcher.fetch(URL)

    assert result.ok
    assert result.content_type is None
    assert result.text is None  # no content-type => we don't assume HTML


@respx.mock
async def test_error_status_reports_status_without_body() -> None:
    respx.get(URL).mock(
        return_value=httpx.Response(
            404, headers={"content-type": "text/html"}, content=b"not found"
        )
    )
    async with HttpxFetcher() as fetcher:
        result = await fetcher.fetch(URL)

    assert result.status_code == 404
    assert result.ok is False
    assert result.text is None
    assert result.error is None  # an HTTP status is not a transport error


@respx.mock
async def test_redirects_are_followed_and_final_url_reported() -> None:
    respx.get("https://example.com/old").mock(
        return_value=httpx.Response(301, headers={"location": "https://example.com/new"})
    )
    respx.get("https://example.com/new").mock(
        return_value=httpx.Response(200, headers={"content-type": "text/html"}, content=b"<a>")
    )
    async with HttpxFetcher() as fetcher:
        result = await fetcher.fetch("https://example.com/old")

    assert result.status_code == 200
    assert result.final_url == "https://example.com/new"
    assert result.text is not None


@pytest.mark.parametrize(
    "side_effect",
    [
        httpx.ConnectError("connection refused"),
        httpx.ConnectTimeout("timed out"),
        httpx.ReadTimeout("read timed out"),
    ],
)
@respx.mock
async def test_transport_errors_become_error_results(side_effect: Exception) -> None:
    respx.get(URL).mock(side_effect=side_effect)
    async with HttpxFetcher() as fetcher:
        result = await fetcher.fetch(URL)

    assert result.ok is False
    assert result.status_code is None
    assert result.error  # a non-empty description
    assert result.final_url == URL


@respx.mock
async def test_html_body_is_capped_at_max_bytes() -> None:
    body = b"<html>" + b"a" * 100_000
    respx.get(URL).mock(
        return_value=httpx.Response(200, headers={"content-type": "text/html"}, content=body)
    )
    async with HttpxFetcher(max_bytes=1_000) as fetcher:
        result = await fetcher.fetch(URL)

    assert result.text is not None
    assert len(result.text) <= 1_000


@respx.mock
async def test_non_utf8_charset_is_decoded() -> None:
    respx.get(URL).mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "text/html; charset=latin-1"},
            content="café".encode("latin-1"),
        )
    )
    async with HttpxFetcher() as fetcher:
        result = await fetcher.fetch(URL)

    assert result.text == "café"


@respx.mock
async def test_sends_identifying_user_agent() -> None:
    route = respx.get(URL).mock(
        return_value=httpx.Response(200, headers={"content-type": "text/html"}, content=b"<a>")
    )
    async with HttpxFetcher() as fetcher:
        await fetcher.fetch(URL)

    assert route.calls.last.request.headers["user-agent"].startswith("site-crawler/")
