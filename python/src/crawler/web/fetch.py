"""HTTP fetching over a shared client; header-first, skipping bodies we won't parse."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import httpx

FetchErrorKind = Literal["status", "non_html", "timeout", "transport"]


@dataclass(frozen=True, slots=True)
class FetchOk:
    """A successful HTML response body as raw bytes."""

    body: bytes


@dataclass(frozen=True, slots=True)
class FetchError:
    """A fetch result we will not turn into a page. ``kind`` drives the outcome."""

    kind: FetchErrorKind
    detail: str


type FetchResult = FetchOk | FetchError


def _media_type(response: httpx.Response) -> str:
    content_type: str = response.headers.get("content-type", "")
    return content_type.split(";", 1)[0].strip().lower()


async def fetch_html(client: httpx.AsyncClient, url: str) -> FetchResult:
    """Fetch ``url``; read the body only for a successful HTML response."""
    try:
        async with client.stream("GET", url) as response:
            if not response.is_success:
                return FetchError("status", str(response.status_code))
            media = _media_type(response)
            if media != "text/html":
                return FetchError("non_html", media or "unknown")
            return FetchOk(await response.aread())
    except httpx.TimeoutException as error:
        return FetchError("timeout", str(error) or type(error).__name__)
    except httpx.HTTPError as error:
        return FetchError("transport", str(error) or type(error).__name__)


async def fetch_robots(client: httpx.AsyncClient, robots_url: str) -> str | None:
    """Return ``robots.txt`` text, or ``None`` for any missing/unreadable result."""
    try:
        response = await client.get(robots_url)
        return response.text if response.is_success else None
    except httpx.HTTPError:
        return None
