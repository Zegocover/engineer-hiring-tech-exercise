"""The URL frontier: scope predicates plus the seen set (synchronous, so no lock is needed)."""

from __future__ import annotations

from collections.abc import Iterable

from crawler.web import urls

from .politeness import Politeness


class Frontier:
    """Decides which discovered links become work, and remembers what was seen."""

    def __init__(self, base_url: str, politeness: Politeness) -> None:
        self._base_host = urls.host(base_url)
        self._politeness = politeness
        self._seen = {urls.dedup_key(base_url)}

    def admit(self, links: Iterable[str]) -> list[str]:
        """In-scope, newly-seen links (HTTP(S), same host, robots-allowed); marks them seen."""
        admitted: list[str] = []
        for link in links:
            if not (
                urls.is_http(link)
                and urls.same_host(link, self._base_host)
                and self._politeness.allowed(link)
            ):
                continue
            key = urls.dedup_key(link)
            if key not in self._seen:
                self._seen.add(key)
                admitted.append(link)
        return admitted
