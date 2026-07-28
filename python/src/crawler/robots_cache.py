import logging
import urllib.parse
from datetime import UTC, datetime, timedelta

import httpx

from crawler.config import USER_AGENT

logger = logging.getLogger(__name__)

# RFC 9309 suggests caching robots.txt for up to 24h; we use a shorter default for the sake of easier the exercise
# so long-running crawls pick up rule changes within a session.
DEFAULT_TTL = timedelta(hours=1)
MAX_TTL = timedelta(hours=24)


class RobotsCache:
    def __init__(
        self,
        client: httpx.AsyncClient,
        user_agent: str = USER_AGENT,
        ttl: timedelta = DEFAULT_TTL,
    ) -> None:
        """`client` is owned by the caller: this cache never closes it, and
        takes its timeout, redirect and header policy from it. `user_agent`
        is the token robots.txt rules are matched against, and must agree
        with the User-Agent header the client sends."""
        self.user_agent = user_agent
        self.ttl = ttl
        self.client = client

        # Cache: { "domain": (expiration, "robots_text_content" | None)}
        self._cache: dict[str, tuple[datetime, str | None]] = {}

    async def fetch_robots_txt(self, url: str) -> str | None:

        domain = self._get_url_domain(url)
        robots_url = f"{domain}/robots.txt"
        now = datetime.now(UTC)

        if domain in self._cache:
            expiration, cached_content = self._cache[domain]
            if now < expiration:
                return cached_content

        try:
            response: httpx.Response = await self.client.get(robots_url)
            content_type: httpx.Headers = response.headers.get(
                "content-type", ""
            ).lower()
            status: int = response.status_code
            page_rules: str = ""

            # Soft-404 guard: many sites serve an HTML error page with a 200 for
            # a missing robots.txt. Parsing that HTML yields junk directives, so
            # we treat a non-text/plain 200 as "no robots.txt" instead. Stricter
            # than RFC 9309, which does not mandate a content type.
            if status == 200 and "text/plain" not in content_type:
                logger.warning(
                    "%s returned 200 but Content-Type is HTML. Treating as 404",
                    domain,
                )
                status = 404

            if status == 200:
                page_rules = response.text
            elif 400 <= status < 500 and status not in (401, 403, 429):
                # 401/403 mean access denied and 429 means rate limited; both
                # are handled below as blocking rather than permissive.
                page_rules = ""
            elif 500 <= status < 600:
                logger.warning(
                    "[BLOCKED] 5xx Server Error (%s) on %s. Skipping crawl.",
                    status,
                    domain,
                )
                return self._store(domain, None, response)
            elif status in (401, 403):
                logger.warning(
                    "[BLOCKED] %s Forbidden on %s robots.txt. Skipping crawl.",
                    status,
                    domain,
                )
                return self._store(domain, None, response)
            else:
                logger.warning("[FAILED] hit unexpected status %s.", status)
                return self._store(domain, None, response)

            return self._store(domain, page_rules, response)

        except httpx.TooManyRedirects:
            logger.warning(
                "[BLOCKED] Redirected too many times exceeded limit of %s for %s",
                self.client.max_redirects,
                domain,
            )
            return self._store(domain, None)
        except httpx.RequestError as e:
            logger.warning(
                "[BLOCKED] Networking error when fetching rules for %s. [ERROR]: %s",
                domain,
                e,
            )
            return self._store(domain, None)

    def _store(
        self,
        domain: str,
        content: str | None,
        response: httpx.Response | None = None,
    ) -> str | None:
        """Caches the outcome for `domain` and returns it unchanged.

        Failures are cached too, so a broken or hostile host is not re-hit on
        every lookup within the TTL.
        """
        self._cache[domain] = (datetime.now(UTC) + self._ttl_for(response), content)
        return content

    def _ttl_for(self, response: httpx.Response | None) -> timedelta:
        """Honours Cache-Control: max-age when present, clamped to MAX_TTL."""
        if response is None:
            return self.ttl
        cache_control = response.headers.get("cache-control", "").lower()
        for directive in cache_control.split(","):
            directive = directive.strip()
            if directive.startswith("max-age="):
                try:
                    return min(timedelta(seconds=int(directive[8:])), MAX_TTL)
                except ValueError:
                    break
        return self.ttl

    def _get_url_domain(self, url: str) -> str:
        """Extracts the scheme and network location (e.g. https://zego.com)"""
        parsed_url = urllib.parse.urlparse(url)
        scheme = parsed_url.scheme
        network_location = parsed_url.netloc
        return f"{scheme}://{network_location}"
