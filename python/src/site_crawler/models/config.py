from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

DEFAULT_USER_AGENT = "site-crawler/0.1 (+https://github.com/)"


class ConfigError(ValueError):
    """Raised when a crawl is configured with invalid values."""


@dataclass(frozen=True, slots=True)
class CrawlConfig:
    base_url: str
    concurrency: int = 16
    max_pages: int | None = None
    max_depth: int | None = None
    timeout: float = 10.0
    respect_robots: bool = True
    user_agent: str = DEFAULT_USER_AGENT

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
