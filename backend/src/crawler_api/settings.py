"""Service-wide settings, read from ``CRAWLER_API_*`` environment variables."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields

from site_crawler.models import DEFAULT_USER_AGENT

ENV_PREFIX = "CRAWLER_API_"

# Field annotations are strings under ``from __future__ import annotations``.
_PARSERS: dict[str, Callable[[str], object]] = {"int": int, "float": float, "str": str}


@dataclass(frozen=True, slots=True)
class Settings:
    default_max_pages: int = 1000
    """Page budget for a crawl that does not set ``max_pages``."""
    max_pages_limit: int = 10_000
    """Largest ``max_pages`` a request may ask for."""
    default_concurrency: int = 8
    max_concurrency: int = 32
    max_connections: int = 100
    """Connections shared by all crawls."""
    request_timeout: float = 10.0
    user_agent: str = DEFAULT_USER_AGENT

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Build settings, overriding defaults with ``CRAWLER_API_<FIELD>`` variables."""
        env = os.environ if environ is None else environ
        overrides: dict[str, object] = {}
        for f in fields(cls):
            raw = env.get(ENV_PREFIX + f.name.upper())
            if raw is None:
                continue
            try:
                overrides[f.name] = _PARSERS[str(f.type)](raw)
            except ValueError as exc:
                raise ValueError(f"{ENV_PREFIX}{f.name.upper()}: invalid value {raw!r}") from exc
        return cls(**overrides)  # type: ignore[arg-type]
