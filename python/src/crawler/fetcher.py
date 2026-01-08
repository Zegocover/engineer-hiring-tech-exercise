"""Async HTTP fetcher using httpx."""

from enum import Enum

import httpx
from pydantic import BaseModel


class FetchError(Enum):
    """Types of fetch errors."""

    NOT_HTML = "not_html"
    HTTP_ERROR = "http_error"
    CONNECTION_ERROR = "connection_error"


class FetchResult(BaseModel):
    """Result of fetching a URL."""

    url: str
    html: str | None = None
    error: FetchError | None = None


async def fetch(client: httpx.AsyncClient, url: str) -> FetchResult:
    """Fetch a URL and return its HTML content.

    Args:
        client: The httpx async client to use.
        url: The URL to fetch.

    Returns:
        FetchResult with html content on success, or error type on failure.
    """
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            return FetchResult(url=url, error=FetchError.NOT_HTML)

        return FetchResult(url=url, html=response.text)

    except httpx.HTTPStatusError:
        return FetchResult(url=url, error=FetchError.HTTP_ERROR)
    except httpx.RequestError:
        return FetchResult(url=url, error=FetchError.CONNECTION_ERROR)
