from typing import Protocol
from urllib.parse import urlsplit


class DomainFilter(Protocol):
    def is_allowed(self, url: str) -> bool: ...


class ExactDomainFilter:
    """Restricts crawling to a single exact hostname (no subdomains, no parent domains)."""

    def __init__(self, base_url: str) -> None:
        hostname = urlsplit(base_url).hostname
        if not hostname:
            raise ValueError(f"Cannot determine hostname from base URL: {base_url!r}")
        self._hostname = hostname.lower()

    def is_allowed(self, url: str) -> bool:
        return urlsplit(url).hostname == self._hostname
