"""HTTP client for one crawl."""

import asyncio
from dataclasses import dataclass

import aiohttp

from site_crawler.url_utils import canonical_url, same_site


@dataclass
class FetchResult:
    url: str
    final_url: str = ""
    html: str = ""
    error: str = ""


class HttpClient:
    """One shared session with a capped connection pool.

    Timeouts, connection errors, and HTTP 4xx/5xx become a ``FetchResult``
    error. They do not raise into the crawl loop.
    """

    def __init__(self, concurrency=10, timeout=10, user_agent="site-crawler/0.1"):
        self.concurrency = concurrency
        self.timeout = timeout
        self.user_agent = user_agent
        self._session = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        connector = aiohttp.TCPConnector(limit=self.concurrency)
        self._session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={"User-Agent": self.user_agent},
        )
        return self

    async def __aexit__(self, *_exc):
        await self._session.close()

    async def fetch(self, url, root_host):
        try:
            async with self._session.get(url, allow_redirects=True) as response:
                final = canonical_url(str(response.url))
                if final and not same_site(final, root_host):
                    return FetchResult(url, error="redirected off-site")
                if response.status >= 400:
                    return FetchResult(url, error="HTTP %s" % response.status)
                content_type = response.headers.get("Content-Type", "")
                if "html" not in content_type.lower():
                    return FetchResult(url, final_url=final or url)
                html = await response.text(errors="replace")
                return FetchResult(url, final_url=final or url, html=html)
        except asyncio.TimeoutError:
            return FetchResult(url, error="timeout")
        except aiohttp.ClientError as exc:
            return FetchResult(url, error=str(exc))
