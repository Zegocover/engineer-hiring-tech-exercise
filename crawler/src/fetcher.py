from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

@dataclass
class FetchResult:
    url: str
    status: int | None
    html: str | None
    error: str | None = None


class Fetcher:
    """Retries/backoff/Retry-After are handled by the client's RetryTransport (httpx-retries).
    this class is only responsible for honoring the crawl delay and turning a response
    into a FetchResult.
    """
    def __init__(
        self,
        client: httpx.AsyncClient,
        min_delay: float = 0.0,
    ) -> None:
        self._client = client
        self._min_delay = min_delay

    async def fetch(self, url: str, *, validate_content_type: bool = True) -> FetchResult:
        if self._min_delay:
            await asyncio.sleep(self._min_delay)
        try:
            response = await self._client.get(url)
        except (httpx.TimeoutException, httpx.TransportError) as e:
            logger.error("giving up on %s: %s", url, e)
            return FetchResult(url=url, status=None, html=None, error=str(e))

        return await self._to_result(response, validate_content_type)

    @staticmethod
    async def _to_result(response: httpx.Response, validate_content_type: bool) -> FetchResult:
        """Turns a completed (non-retryable) response into a FetchResult, closing it."""
        if response.status_code != 200:
            logger.warning("got HTTP %d for %s, giving up", response.status_code, response.url)
            await response.aclose()
            return FetchResult(
                url=str(response.url),
                status=response.status_code,
                html=None,
                error=f"HTTP {response.status_code}",
            )

        if validate_content_type:
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type:
                await response.aclose()
                return FetchResult(
                    url=str(response.url),
                    status=response.status_code,
                    html=None,
                    error=f"unsupported content-type: {content_type}",
                )

        return FetchResult(url=str(response.url), status=response.status_code, html=response.text)
