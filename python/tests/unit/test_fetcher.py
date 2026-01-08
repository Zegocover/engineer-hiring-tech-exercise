"""Tests for HTTP fetcher."""

import httpx
import pytest

from crawler.fetcher import FetchError, fetch


@pytest.fixture
def mock_client(mocker):
    return mocker.AsyncMock(spec=httpx.AsyncClient)


async def test_fetch_returns_html_on_success(mock_client) -> None:
    mock_response = httpx.Response(
        200,
        content=b"<html><body>Hello</body></html>",
        headers={"content-type": "text/html"},
        request=httpx.Request("GET", "https://example.com"),
    )
    mock_client.get.return_value = mock_response

    result = await fetch(mock_client, "https://example.com")

    assert result.html == "<html><body>Hello</body></html>"
    assert result.error is None


async def test_fetch_returns_not_html_error_for_json(mock_client) -> None:
    mock_response = httpx.Response(
        200,
        content=b"{}",
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://example.com/api"),
    )
    mock_client.get.return_value = mock_response

    result = await fetch(mock_client, "https://example.com/api")

    assert result.html is None
    assert result.error is FetchError.NOT_HTML


async def test_fetch_returns_http_error_for_404(mock_client) -> None:
    mock_response = httpx.Response(404, request=httpx.Request("GET", "https://example.com"))
    mock_client.get.return_value = mock_response

    result = await fetch(mock_client, "https://example.com/missing")

    assert result.html is None
    assert result.error is FetchError.HTTP_ERROR


async def test_fetch_returns_connection_error_on_failure(mock_client) -> None:
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")

    result = await fetch(mock_client, "https://example.com")

    assert result.html is None
    assert result.error is FetchError.CONNECTION_ERROR
