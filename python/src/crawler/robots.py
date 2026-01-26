"""robots.txt handling and policy helpers."""

import logging
import urllib.parse as parse
import urllib.request as request
from dataclasses import dataclass


@dataclass(frozen=True)
class RobotsPolicy:
    """Simple robots.txt policy for User-agent: * rules."""

    allow: tuple[str, ...]
    disallow: tuple[str, ...]

    def is_allowed(self, url: str) -> bool:
        """Return True if the URL path is allowed by this policy."""
        path = parse.urlparse(url).path or "/"
        for prefix in self.allow:
            if path.startswith(prefix):
                return True
        for prefix in self.disallow:
            if path.startswith(prefix):
                return False
        return True


def robots_url_for(url: str) -> str:
    """Build the robots.txt URL for a given page URL."""
    parsed = parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL for robots.txt: {url}")
    return parse.urlunparse(
        (parsed.scheme, parsed.netloc, "/robots.txt", "", "", "")
    )


def parse_robots_txt(text: str) -> RobotsPolicy:
    """Parse a minimal robots.txt for User-agent: * rules."""
    allow: list[str] = []
    disallow: list[str] = []
    applies = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()

        if key == "user-agent":
            applies = value == "*"
            continue

        if not applies:
            continue

        if key == "allow" and value:
            allow.append(value)
        if key == "disallow" and value:
            disallow.append(value)

    return RobotsPolicy(allow=tuple(allow), disallow=tuple(disallow))


def fetch_robots_policy(
    url: str,
    user_agent: str,
    timeout_s: int,
) -> RobotsPolicy:
    """Fetch and parse robots.txt for the given URL (sync)."""
    robots_url = robots_url_for(url)
    req = request.Request(robots_url, headers={"User-Agent": user_agent})

    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            if resp.status >= 300:
                logging.info(
                    "robots.txt returned %s, defaulting to allow-all",
                    resp.status,
                )
                return RobotsPolicy(allow=(), disallow=())
            text = resp.read().decode("utf-8", errors="replace")
            return parse_robots_txt(text)
    except Exception:
        logging.info("robots.txt fetch failed, defaulting to allow-all")
        return RobotsPolicy(allow=(), disallow=())
