"""HTTP fetching utilities and response handling."""

from dataclasses import dataclass

import aiohttp


@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int
    content_type: str | None
    body: str


class FetchError(Exception):
    """Base exception for fetch failures."""


class RetryableFetchError(FetchError):
    """Fetch failed but may succeed if retried."""

    def __init__(self, message: str, retry_after: str | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class NonRetryableFetchError(FetchError):
    """Fetch failed and should not be retried."""


class RedirectFetchError(FetchError):
    """Fetch received a redirect; caller can decide how to handle it."""

    def __init__(self, url: str, location: str | None) -> None:
        super().__init__(f"Redirect from {url} to {location}")
        self.url = url
        self.location = location


class UnsupportedContentTypeError(NonRetryableFetchError):
    """Fetch succeeded but content type is unsupported."""


class Fetcher:
    """HTTP fetcher that owns a reusable aiohttp session."""

    def __init__(self, user_agent: str, timeout_s: int) -> None:
        self._user_agent = user_agent
        self._timeout = aiohttp.ClientTimeout(total=timeout_s)
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "Fetcher":
        self._session = aiohttp.ClientSession(
            timeout=self._timeout,
            headers={"User-Agent": self._user_agent},
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def fetch_html(self, url: str) -> FetchResult:
        """Fetch a URL and return HTML, or raise an appropriate error."""
        if self._session is None:
            raise RuntimeError("Fetcher session not initialised")

        try:
            async with self._session.get(
                url, allow_redirects=False
            ) as response:
                status = response.status
                content_type = response.headers.get("Content-Type")

                if 300 <= status < 400:
                    location = response.headers.get("Location")
                    raise RedirectFetchError(url, location)

                if status == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise RetryableFetchError(
                        f"429 Too Many Requests: {url}",
                        retry_after=retry_after,
                    )

                if 400 <= status < 500:
                    raise NonRetryableFetchError(
                        f"{status} Client error: {url}"
                    )

                if 500 <= status < 600:
                    raise RetryableFetchError(f"{status} Server error: {url}")

                if content_type and "text/html" not in content_type:
                    raise UnsupportedContentTypeError(
                        f"Unsupported content type: {content_type}"
                    )

                body = await response.text()
                return FetchResult(
                    url=url,
                    status=status,
                    content_type=content_type,
                    body=body,
                )
        except aiohttp.ClientError as exc:
            raise RetryableFetchError(f"Network error: {url}") from exc
