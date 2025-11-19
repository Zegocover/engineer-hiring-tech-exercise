"""Simple robots.txt support used by the crawler.

This module provides a small, permissive `RobotsParser` used to fetch
and interpret a host's `robots.txt`. It supports basic `User-agent`,
`Allow`, `Disallow` and `Crawl-delay` directives. The parser is
intentionally lightweight — it covers common directives the crawler
needs and is not a full robots.txt implementation.
"""

from urllib.parse import urljoin, urlparse
from typing import Optional


class RobotsParser:
    """Naive robots.txt parser.

    - Exact user-agent rules take precedence; otherwise `*` rules are used.
    - `Allow` rules win over `Disallow` when both match.
    - An empty `Disallow:` is treated as allow-all.
    """

    def __init__(self, base_url: str, text: str):
        self.base_url = base_url
        self.rules = {}  # user-agent -> {'allow':[], 'disallow':[], 'crawl_delay': float}
        self._parse(text)

    @classmethod
    async def fetch(cls, session, base_url: str):
        parsed = urlparse(base_url)
        robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
        try:
            async with session.get(robots_url, timeout=10) as resp:
                if resp.status != 200:
                    return cls(base_url, "")
                text = await resp.text()
                return cls(base_url, text)
        except Exception:
            return cls(base_url, "")

    def _parse(self, text: str):
        ua = None
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.strip().lower()
            v = v.strip()
            if k == "user-agent":
                ua = v
                if ua not in self.rules:
                    self.rules[ua] = {"allow": [], "disallow": [], "crawl_delay": None}
            elif k == "disallow" and ua is not None:
                self.rules[ua]["disallow"].append(v)
            elif k == "allow" and ua is not None:
                self.rules[ua]["allow"].append(v)
            elif k == "crawl-delay" and ua is not None:
                try:
                    self.rules[ua]["crawl_delay"] = float(v)
                except Exception:
                    pass

    def _matching_rules(self, path: str, ua: str):
        # find best matching user-agent: exact match otherwise '*'
        if ua in self.rules:
            return self.rules[ua]
        if "*" in self.rules:
            return self.rules["*"]
        return {"allow": [], "disallow": [], "crawl_delay": None}

    def is_allowed(self, url: str, ua: str = "*") -> bool:
        parsed = urlparse(url)
        path = parsed.path or "/"
        rules = self._matching_rules(path, ua)
        # allow takes precedence over disallow for naive parser
        for a in rules["allow"]:
            if path.startswith(a):
                return True
        for d in rules["disallow"]:
            if d == "":
                # empty disallow means allow all
                return True
            if path.startswith(d):
                return False
        return True

    def get_crawl_delay(self, ua: str = "*") -> Optional[float]:
        rules = self._matching_rules("/", ua)
        return rules.get("crawl_delay")
