"""Robots policy. Only a no-op placeholder exists today.

PRODUCTION GAP: a real implementation must fetch and cache each origin's
/robots.txt, honor Disallow rules and Crawl-delay, and deny on parse failure.
This must be implemented before running against third-party sites in production.
"""

from domains.crawler.ports import RobotsPolicy


class NoOpRobotsPolicy(RobotsPolicy):
    """Allows every URL. Placeholder so the fetch stage already has the seam."""

    async def allowed(self, url: str) -> bool:
        return True
