"""Immutable data passed through the crawl pipeline. No I/O, no behavior."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FetchResult:
    """Outcome of fetching one URL. `html` is None when not fetched/parsed."""

    requested_url: str
    final_url: str
    status: int | None
    content_type: str | None
    html: str | None
    error: str | None


@dataclass(frozen=True, slots=True)
class PageResult:
    """A crawled page and every link found on it (links sorted, deduped)."""

    url: str
    links: tuple[str, ...]
    status: int | None
    error: str | None


@dataclass(frozen=True, slots=True)
class ParseOutcome:
    """A parsed page plus its on-host link candidates (pre-dedup, for the engine)."""

    page: PageResult
    on_host_links: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CrawlConfig:
    """Everything the engine and parse stage need to run one crawl."""

    seed_url: str
    seed_host: str
    concurrency: int = 10
    timeout: float = 10.0
    max_pages: int | None = None
    user_agent: str = "crawler/0.1 (+https://example.com/bot)"
    max_bytes: int = 5_000_000
