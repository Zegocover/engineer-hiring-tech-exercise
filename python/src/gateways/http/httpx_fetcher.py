"""Fetcher port implemented with httpx. Never raises: network failures are
returned as FetchResult(error=...). Only text/html bodies are returned."""

import httpx

from domains.crawler.models import FetchResult

_HTML_TYPE = "text/html"


class HttpxFetcher:
    """Fetches URLs via a shared httpx.AsyncClient (pooling/keep-alive)."""

    def __init__(self, client: httpx.AsyncClient, max_bytes: int = 5_000_000) -> None:
        self._client = client
        self._max_bytes = max_bytes

    async def fetch(self, url: str) -> FetchResult:
        try:
            response = await self._client.get(url, follow_redirects=True)
        except httpx.HTTPError as exc:
            return FetchResult(
                requested_url=url,
                final_url=url,
                status=None,
                content_type=None,
                html=None,
                error=f"{type(exc).__name__}: {exc}",
            )

        content_type = response.headers.get("content-type")
        # Media types are case-insensitive (RFC 7231), so a server sending
        # "Text/HTML" must still count as HTML. Compare lowercased; store original.
        is_html = content_type is not None and content_type.lower().startswith(_HTML_TYPE)
        body = response.text if is_html and len(response.content) <= self._max_bytes else None
        return FetchResult(
            requested_url=url,
            final_url=str(response.url),
            status=response.status_code,
            content_type=content_type,
            html=body,
            error=None,
        )
