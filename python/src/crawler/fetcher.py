"""HTTP fetching, isolated behind a ``Fetcher`` protocol so it can be faked in tests."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, runtime_checkable

import httpx

from crawler import __version__
from crawler.models import FetchResult

DEFAULT_USER_AGENT = f"site-crawler/{__version__}"
DEFAULT_TIMEOUT = 10.0
DEFAULT_MAX_BYTES = 5_000_000

_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_READ_CHUNK = 65_536


@runtime_checkable
class Fetcher(Protocol):
    """Fetches a URL and reports the outcome, never raising for HTTP errors."""

    async def fetch(self, url: str) -> FetchResult: ...


class HttpxFetcher:
    """A :class:`Fetcher` backed by a pooled :class:`httpx.AsyncClient`."""

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
        max_bytes: int = DEFAULT_MAX_BYTES,
        follow_redirects: bool = True,
    ) -> None:
        self._max_bytes = max_bytes
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=follow_redirects,
            headers={"User-Agent": user_agent},
        )

    async def __aenter__(self) -> HttpxFetcher:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying connection pool."""
        await self._client.aclose()

    async def fetch(self, url: str) -> FetchResult:
        try:
            async with self._client.stream("GET", url) as response:
                content_type = response.headers.get("content-type")
                if response.status_code >= 400 or not _is_html(content_type):
                    # Nothing we want to parse — don't download the body.
                    return FetchResult(
                        requested_url=url,
                        final_url=str(response.url),
                        status_code=response.status_code,
                        content_type=content_type,
                    )
                return FetchResult(
                    requested_url=url,
                    final_url=str(response.url),
                    status_code=response.status_code,
                    content_type=content_type,
                    text=await self._read_text(response),
                )
        except httpx.HTTPError as exc:
            # Report transport failures rather than raising, so one bad URL
            # never brings the crawl down.
            return FetchResult(requested_url=url, final_url=url, error=_describe(exc))

    async def _read_text(self, response: httpx.Response) -> str:
        # Cap *retained* bytes at max_bytes so a pathological page can't exhaust
        # memory, but drain the stream to completion so httpx closes it cleanly
        # (breaking out early leaks its internal byte generators).
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes(_READ_CHUNK):
            if total < self._max_bytes:
                chunks.append(chunk)
                total += len(chunk)
        raw = b"".join(chunks)[: self._max_bytes]
        return raw.decode(response.encoding or "utf-8", errors="replace")


def _is_html(content_type: str | None) -> bool:
    if not content_type:
        return False
    return content_type.split(";", 1)[0].strip().lower() in _HTML_TYPES


def _describe(exc: Exception) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__
