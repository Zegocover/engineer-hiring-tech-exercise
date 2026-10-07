from __future__ import annotations

import logging
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

from site_crawler.interfaces import Fetcher
from site_crawler.models import FetchError

logger = logging.getLogger(__name__)


class RobotsGate:
    """Answers whether a URL may be fetched according to the host's robots.txt.

    A missing or unreachable robots.txt allows everything, matching common
    crawler behaviour. ``Crawl-delay`` is not honoured.
    """

    def __init__(self, rules: RobotFileParser | None, user_agent: str) -> None:
        self._rules = rules
        self._user_agent = user_agent

    @classmethod
    async def load(cls, fetcher: Fetcher, origin: str, user_agent: str) -> RobotsGate:
        """Fetch and parse ``robots.txt`` for the host at ``origin`` (``scheme://host/``)."""
        robots_url = urljoin(origin, "/robots.txt")
        try:
            page = await fetcher.fetch(robots_url)
        except FetchError as exc:
            logger.info("no usable robots.txt (%s); allowing all", exc.reason)
            return cls(None, user_agent)
        if page.status >= 400:
            return cls(None, user_agent)
        rules = RobotFileParser(robots_url)
        rules.parse(page.body.decode("utf-8", errors="replace").splitlines())
        return cls(rules, user_agent)

    def allowed(self, url: str) -> bool:
        return self._rules is None or self._rules.can_fetch(self._user_agent, url)
