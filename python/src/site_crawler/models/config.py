from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from site_crawler.models.errors import ConfigError
from site_crawler.models.hosts import HostPattern, parse_host_pattern

DEFAULT_USER_AGENT = "site-crawler/0.1 (+https://github.com/)"


@dataclass(frozen=True, slots=True)
class CrawlConfig:
    base_url: str
    concurrency: int = 16
    max_pages: int | None = None
    max_depth: int | None = None
    timeout: float = 10.0
    respect_robots: bool = True
    user_agent: str = DEFAULT_USER_AGENT
    allowed_hosts: tuple[str, ...] = ()
    """Host patterns followed besides the base host (see :func:`parse_host_pattern`).

    Stored normalised and without duplicates, e.g. ``("*.example.com", "docs.partner.io")``.
    """
    per_host_concurrency: int | None = None
    """Most requests in flight to any one host; ``None`` means no limit beyond ``concurrency``."""

    def __post_init__(self) -> None:
        parts = urlsplit(self.base_url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ConfigError(f"base URL must be an absolute http(s) URL, got {self.base_url!r}")
        if self.concurrency < 1:
            raise ConfigError("concurrency must be at least 1")
        if self.max_pages is not None and self.max_pages < 1:
            raise ConfigError("max_pages must be at least 1")
        if self.max_depth is not None and self.max_depth < 0:
            raise ConfigError("max_depth must not be negative")
        if self.timeout <= 0:
            raise ConfigError("timeout must be positive")
        if self.per_host_concurrency is not None and self.per_host_concurrency < 1:
            raise ConfigError("per_host_concurrency must be at least 1")
        patterns = dict.fromkeys(str(parse_host_pattern(p)) for p in self.allowed_hosts)
        object.__setattr__(self, "allowed_hosts", tuple(patterns))  # frozen dataclass

    @property
    def host_patterns(self) -> tuple[HostPattern, ...]:
        return tuple(parse_host_pattern(p) for p in self.allowed_hosts)
