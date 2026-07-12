from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

import httpx

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


@dataclass
class FetchResult:
    url: str
    status: int | None
    html: str | None
    error: str | None = None


class Fetcher:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        backoff_cap: float = 8.0,
    ) -> None:
        self._client = client
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_cap = backoff_cap

    async def fetch(self, url: str) -> FetchResult:
        last_error: str | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.get(url)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = str(exc)
                await self._backoff(attempt)
                continue

            if response.status_code in _RETRYABLE_STATUS:
                last_error = f"HTTP {response.status_code}"
                await response.aclose()
                await self._backoff(attempt)
                continue

            if response.status_code != 200:
                await response.aclose()
                return FetchResult(
                    url=str(response.url),
                    status=response.status_code,
                    html=None,
                    error=f"HTTP {response.status_code}",
                )

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type:
                await response.aclose()
                return FetchResult(
                    url=str(response.url),
                    status=response.status_code,
                    html=None,
                    error=f"unsupported content-type: {content_type}",
                )

            return FetchResult(
                url=str(response.url), status=response.status_code, html=response.text
            )

        return FetchResult(
            url=url, status=None, html=None, error=last_error or "max retries exceeded"
        )

    async def _backoff(self, attempt: int) -> None:
        """Exponential backoff, we should look into replacing it with a proper library for httpx"""
        delay = min(self._backoff_cap, self._backoff_base * (2**attempt))
        delay += random.uniform(0, delay * 0.1)
        await asyncio.sleep(delay)
