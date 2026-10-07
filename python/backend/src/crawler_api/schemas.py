"""Request and response bodies of the HTTP API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from crawler_api.jobs import CrawlJob, JobStatus

MAX_ALLOWED_HOSTS = 50


class CrawlRequest(BaseModel):
    url: str = Field(description="Absolute http(s) base URL; its host is the crawl scope.")
    max_pages: int | None = Field(
        default=None, ge=1, description="Page budget. Defaults to the service's default budget."
    )
    max_depth: int | None = Field(default=None, ge=0, description="Link hops from the base URL.")
    concurrency: int | None = Field(default=None, ge=1, description="Parallel requests.")
    per_host_concurrency: int | None = Field(
        default=None, ge=1, description="Most parallel requests to any one host. Default: no limit."
    )
    respect_robots: bool = True
    allowed_hosts: list[str] = Field(
        default_factory=list,
        max_length=MAX_ALLOWED_HOSTS,
        description="Extra hosts to follow besides the base URL's: 'docs.example.org', "
        "'localhost:8001', or '*.example.com' for any subdomain.",
    )


class Stats(BaseModel):
    pages: int
    fetched: int
    errors: int
    robots_skipped: int


class Limits(BaseModel):
    max_pages: int | None
    max_depth: int | None
    concurrency: int
    per_host_concurrency: int | None
    respect_robots: bool
    allowed_hosts: list[str]


class CrawlStatus(BaseModel):
    """What a client polls: small and cheap."""

    id: str
    status: JobStatus
    started_at: datetime
    finished_at: datetime | None
    stats: Stats
    error: str | None

    @classmethod
    def of(cls, job: CrawlJob) -> CrawlStatus:
        return cls(
            id=job.id,
            status=job.status,
            started_at=job.started_at,
            finished_at=job.finished_at,
            stats=_stats(job),
            error=job.error,
        )


class CrawlSummary(BaseModel):
    id: str
    url: str
    status: JobStatus
    started_at: datetime
    finished_at: datetime | None
    stats: Stats

    @classmethod
    def of(cls, job: CrawlJob) -> CrawlSummary:
        return cls(
            id=job.id,
            url=job.config.base_url,
            status=job.status,
            started_at=job.started_at,
            finished_at=job.finished_at,
            stats=_stats(job),
        )


class CrawlDetail(CrawlSummary):
    limits: Limits
    error: str | None

    @classmethod
    def of(cls, job: CrawlJob) -> CrawlDetail:
        config = job.config
        return cls(
            **CrawlSummary.of(job).model_dump(),
            limits=Limits(
                max_pages=config.max_pages,
                max_depth=config.max_depth,
                concurrency=config.concurrency,
                per_host_concurrency=config.per_host_concurrency,
                respect_robots=config.respect_robots,
                allowed_hosts=list(config.allowed_hosts),
            ),
            error=job.error,
        )


class Page(BaseModel):
    url: str
    links: list[str]


class PageList(BaseModel):
    total: int
    offset: int
    limit: int
    items: list[Page]


class LinkList(BaseModel):
    """Distinct links found anywhere in the crawl, in first-seen order."""

    total: int
    offset: int
    limit: int
    items: list[str]


def _stats(job: CrawlJob) -> Stats:
    s = job.stats
    return Stats(pages=s.pages, fetched=s.fetched, errors=s.errors, robots_skipped=s.robots_skipped)
