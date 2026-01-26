"""Tests for the HTTP fetcher."""

import pytest
from aioresponses import aioresponses

from crawler.fetcher import (
    Fetcher,
    NonRetryableFetchError,
    RedirectFetchError,
    RetryableFetchError,
    UnsupportedContentTypeError,
)


@pytest.mark.asyncio
async def test_fetch_html_success() -> None:
    url = "https://example.com"
    with aioresponses() as mocked:
        mocked.get(
            url,
            status=200,
            headers={"Content-Type": "text/html"},
            body="<html></html>",
        )
        async with Fetcher(user_agent="test", timeout_s=5) as fetcher:
            result = await fetcher.fetch_html(url)

    assert result.url == url
    assert result.status == 200
    assert result.content_type == "text/html"
    assert result.body == "<html></html>"


@pytest.mark.parametrize(
    ("status", "exc_type"),
    [
        pytest.param(404, NonRetryableFetchError, id="404-client"),
        pytest.param(503, RetryableFetchError, id="503-retry"),
    ],
)
@pytest.mark.asyncio
async def test_fetch_html_status_errors(status: int, exc_type) -> None:
    url = "https://example.com"
    with aioresponses() as mocked:
        mocked.get(url, status=status, headers={"Content-Type": "text/html"})
        async with Fetcher(user_agent="test", timeout_s=5) as fetcher:
            with pytest.raises(exc_type):
                await fetcher.fetch_html(url)


@pytest.mark.asyncio
async def test_fetch_html_redirect() -> None:
    url = "https://example.com"
    with aioresponses() as mocked:
        mocked.get(
            url, status=302, headers={"Location": "https://example.com/new"}
        )
        async with Fetcher(user_agent="test", timeout_s=5) as fetcher:
            with pytest.raises(RedirectFetchError) as exc:
                await fetcher.fetch_html(url)

    assert exc.value.location == "https://example.com/new"


@pytest.mark.asyncio
async def test_fetch_html_unsupported_content_type() -> None:
    url = "https://example.com"
    with aioresponses() as mocked:
        mocked.get(
            url,
            status=200,
            headers={"Content-Type": "application/json"},
            body="{}",
        )
        async with Fetcher(user_agent="test", timeout_s=5) as fetcher:
            with pytest.raises(UnsupportedContentTypeError):
                await fetcher.fetch_html(url)


@pytest.mark.asyncio
async def test_fetch_html_retry_after_on_429() -> None:
    url = "https://example.com"
    with aioresponses() as mocked:
        mocked.get(url, status=429, headers={"Retry-After": "120"})
        async with Fetcher(user_agent="test", timeout_s=5) as fetcher:
            with pytest.raises(RetryableFetchError) as exc:
                await fetcher.fetch_html(url)

    assert exc.value.retry_after == "120"
