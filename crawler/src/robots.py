from __future__ import annotations

from typing import Protocol
from urllib.parse import urlsplit

from protego import Protego

from .fetcher import Fetcher


class RobotsPolicy(Protocol):
    @property
    def crawl_delay(self) -> float | None: ...

    def is_allowed(self, url: str) -> bool: ...


class ProtegoRobotsPolicy:
    def __init__(self, robots_txt: str, user_agent: str) -> None:
        self._parser = Protego.parse(robots_txt)
        self._user_agent = user_agent

    @property
    def crawl_delay(self) -> float | None:
        return self._parser.crawl_delay(self._user_agent)

    def is_allowed(self, url: str) -> bool:
        return self._parser.can_fetch(url, self._user_agent)


def _robots_txt_url(base_url: str) -> str:
    parts = urlsplit(base_url)
    return f"{parts.scheme}://{parts.netloc}/robots.txt"


async def load_robots_policy(
    base_url: str, fetcher: Fetcher, user_agent: str
) -> ProtegoRobotsPolicy:
    """Fetches and parses robots.txt before any page is crawled.

    Fails open (treats everything as allowed, no crawl delay) if robots.txt
    can't be fetched at all, a missing or unreachable robots.txt means no
    restrictions.
    """
    result = await fetcher.fetch(_robots_txt_url(base_url), validate_content_type=False)
    return ProtegoRobotsPolicy(result.html or "", user_agent)
