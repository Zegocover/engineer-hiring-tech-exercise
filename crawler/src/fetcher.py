from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

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
        min_delay: float = 0.0,
    ) -> None:
        self._client = client
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_cap = backoff_cap
        self._min_delay = min_delay

    async def fetch(self, url: str, *, validate_content_type: bool = True) -> FetchResult:
        last_error: str | None = None

        for attempt in range(self._max_retries + 1):
            if self._min_delay:
                await asyncio.sleep(self._min_delay)
            try:
                response = await self._client.get(url)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_error = str(e)
                await self._backoff(attempt)
                continue

            if response.status_code in _RETRYABLE_STATUS:
                last_error = f"HTTP {response.status_code}"
                retry_after = self._parse_retry_after(response)
                await response.aclose()
                await self._backoff(attempt, retry_after)
                continue

            return await self._to_result(response, validate_content_type)

        return FetchResult(
            url=url, status=None, html=None, error=last_error or "max retries exceeded"
        )

    @staticmethod
    async def _to_result(response: httpx.Response, validate_content_type: bool) -> FetchResult:
        """Turns a completed (non-retryable) response into a FetchResult, closing it."""
        if response.status_code != 200:
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

    async def _backoff(self, attempt: int, retry_after: float | None = None) -> None:
        if retry_after is not None:
            delay = min(retry_after, self._backoff_cap)
        else:
            delay = min(self._backoff_cap, self._backoff_base * (2**attempt))
            delay += random.uniform(0, delay * 0.1)
        await asyncio.sleep(delay)

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> float | None:
        value = response.headers.get("retry-after")
        if value is None:
            return None

        if value.strip().isdigit():
            return float(value)

        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None

        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)

        return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
