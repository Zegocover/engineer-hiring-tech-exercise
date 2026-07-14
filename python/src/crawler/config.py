"""Immutable configuration for a crawl run.

Centralising the config here keeps the CLI a thin adapter and lets other entry
points drive a crawl without going through ``argparse``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from crawler.crawler import DEFAULT_CONCURRENCY
from crawler.fetcher import DEFAULT_MAX_BYTES, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT

OutputFormat = Literal["text", "json"]


@dataclass(frozen=True, slots=True)
class CrawlConfig:
    base_url: str
    concurrency: int = DEFAULT_CONCURRENCY
    timeout: float = DEFAULT_TIMEOUT
    max_pages: int | None = None
    user_agent: str = DEFAULT_USER_AGENT
    include_subdomains: bool = False
    output_format: OutputFormat = "text"
    max_bytes: int = DEFAULT_MAX_BYTES
