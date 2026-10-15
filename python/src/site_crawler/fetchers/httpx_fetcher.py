from __future__ import annotations

import asyncio
import logging
import random

import httpx

from site_crawler.models import DEFAULT_USER_AGENT, FetchError, FetchResult

logger = logging.getLogger(__name__)

RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
_TEXT_TYPES = ("application/xhtml+xml", "application/xml", "application/json")


class DefaultHttpxFetcher:
    """Default fetcher: one pooled ``httpx.AsyncClient`` shared by all workers.

    Transient failures (timeouts, connection errors, 429 and 5xx) are retried
    with exponential backoff and jitter, honouring ``Retry-After`` up to
    ``max_retry_after`` seconds. Bodies are downloaded only for textual
    responses (HTML, robots.txt, ...) and capped at ``max_body_bytes``;
    binary resources such as PDFs and images are not downloaded.
    """

    def __init__(
        self,
        *,
        timeout: float = 10.0,
        max_connections: int = 16,
        user_agent: str = DEFAULT_USER_AGENT,
        max_retries: int = 2,
        backoff: float = 0.5,
        max_retry_after: float = 30.0,
        max_body_bytes: int = 10 * 1024 * 1024,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = client or httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            limits=httpx.Limits(
                max_connections=max_connections, max_keepalive_connections=max_connections
            ),
            headers={"User-Agent": user_agent},
        )
        self._max_retries = max_retries
        self._backoff = backoff
        self._max_retry_after = max_retry_after
        self._max_body_bytes = max_body_bytes

    async def fetch(self, url: str) -> FetchResult:
        attempt = 0
        while True:
            try:
                result, retry_after = await self._fetch_once(url)
            except httpx.TransportError as exc:  # includes timeouts
                if attempt >= self._max_retries:
                    raise FetchError(url, f"{type(exc).__name__}: {exc}") from exc
                delay = self._delay(attempt, None)
            except (httpx.HTTPError, httpx.InvalidURL) as exc:  # e.g. too many redirects
                raise FetchError(url, f"{type(exc).__name__}: {exc}") from exc
            else:
                if result.status in RETRYABLE_STATUSES and attempt < self._max_retries:
                    delay = self._delay(attempt, retry_after)
                elif result.status >= 400:
                    raise FetchError(url, f"HTTP {result.status}")
                else:
                    return result
            logger.debug("retrying %s in %.2fs (attempt %d)", url, delay, attempt + 1)
            await asyncio.sleep(delay)
            attempt += 1

    async def _fetch_once(self, url: str) -> tuple[FetchResult, float | None]:
        async with self._client.stream("GET", url) as response:
            content_type = response.headers.get("content-type")
            body = b""
            if response.is_success and _is_textual(content_type):
                body = await self._read_capped(response)
            return (
                FetchResult(
                    url=url,
                    final_url=str(response.url),
                    status=response.status_code,
                    content_type=content_type,
                    body=body,
                ),
                _parse_retry_after(response.headers.get("retry-after")),
            )

    async def _read_capped(self, response: httpx.Response) -> bytes:
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            chunks.append(chunk)
            size += len(chunk)
            if size >= self._max_body_bytes:
                logger.warning("truncated %s at %d bytes", response.url, self._max_body_bytes)
                break
        return b"".join(chunks)[: self._max_body_bytes]

    def _delay(self, attempt: int, retry_after: float | None) -> float:
        if retry_after is not None:
            return min(retry_after, self._max_retry_after)
        base = self._backoff * 2.0**attempt
        return base + random.uniform(0, base)

    async def aclose(self) -> None:
        await self._client.aclose()


def _is_textual(content_type: str | None) -> bool:
    if content_type is None:
        return True  # unknown: download (capped) rather than miss a page
    mime = content_type.split(";", 1)[0].strip().lower()
    return mime.startswith("text/") or mime in _TEXT_TYPES


def _parse_retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None  # HTTP-date form: fall back to exponential backoff
