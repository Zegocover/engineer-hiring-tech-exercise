"""Stage 1: apply the robots gate, then fetch. URL -> FetchResult."""

from domains.crawler.models import FetchResult
from domains.crawler.ports import Fetcher, RobotsPolicy


class DefaultFetchStage:
    """Robots-gates a URL, then delegates to the Fetcher port."""

    def __init__(self, fetcher: Fetcher, robots: RobotsPolicy) -> None:
        self._fetcher = fetcher
        self._robots = robots

    async def fetch(self, url: str) -> FetchResult:
        if not await self._robots.allowed(url):
            return FetchResult(
                requested_url=url,
                final_url=url,
                status=None,
                content_type=None,
                html=None,
                error="disallowed by robots policy",
            )
        return await self._fetcher.fetch(url)
