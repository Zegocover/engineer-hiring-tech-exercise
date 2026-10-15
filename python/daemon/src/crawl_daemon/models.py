"""Crawl jobs, their limits and statistics, and the errors the daemon reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from site_crawler.models import CrawlConfig, CrawlStats


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def finished(self) -> bool:
        return self not in (JobStatus.QUEUED, JobStatus.RUNNING)


def utcnow() -> datetime:
    return datetime.now(UTC)


def _time(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat(timespec="microseconds")


def _parse_time(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


@dataclass(frozen=True, slots=True)
class JobLimits:
    """The limits a job actually runs with, after the daemon's defaults are applied."""

    max_pages: int
    concurrency: int
    max_depth: int | None = None
    per_host_concurrency: int | None = None
    respect_robots: bool = True
    allowed_hosts: tuple[str, ...] = ()

    @classmethod
    def from_config(cls, config: CrawlConfig) -> JobLimits:
        if config.max_pages is None:  # the scheduler always sets a budget
            raise ValueError("a job needs a page budget")
        return cls(
            max_pages=config.max_pages,
            concurrency=config.concurrency,
            max_depth=config.max_depth,
            per_host_concurrency=config.per_host_concurrency,
            respect_robots=config.respect_robots,
            allowed_hosts=config.allowed_hosts,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_pages": self.max_pages,
            "concurrency": self.concurrency,
            "max_depth": self.max_depth,
            "per_host_concurrency": self.per_host_concurrency,
            "respect_robots": self.respect_robots,
            "allowed_hosts": list(self.allowed_hosts),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobLimits:
        return cls(
            max_pages=data["max_pages"],
            concurrency=data["concurrency"],
            max_depth=data.get("max_depth"),
            per_host_concurrency=data.get("per_host_concurrency"),
            respect_robots=data.get("respect_robots", True),
            allowed_hosts=tuple(data.get("allowed_hosts", ())),
        )


@dataclass(slots=True)
class JobStats:
    pages: int = 0
    """Pages reported by the crawl."""
    fetched: int = 0
    errors: int = 0
    robots_skipped: int = 0
    parse_cache_hits: int = 0
    """Pages whose links came from the parse cache instead of the parser."""

    @classmethod
    def from_crawl(cls, stats: CrawlStats, parse_cache_hits: int) -> JobStats:
        return cls(
            pages=stats.pages,
            fetched=stats.fetched,
            errors=stats.errors,
            robots_skipped=stats.robots_skipped,
            parse_cache_hits=parse_cache_hits,
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "pages": self.pages,
            "fetched": self.fetched,
            "errors": self.errors,
            "robots_skipped": self.robots_skipped,
            "parse_cache_hits": self.parse_cache_hits,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobStats:
        return cls(**{key: int(data.get(key, 0)) for key in cls().to_dict()})


@dataclass(slots=True)
class JobRecord:
    """One crawl job: what was asked for, where it is up to and how it ended."""

    id: str
    url: str
    limits: JobLimits
    status: JobStatus
    submitted_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    stats: JobStats = field(default_factory=JobStats)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "status": str(self.status),
            "limits": self.limits.to_dict(),
            "submitted_at": _time(self.submitted_at),
            "started_at": _time(self.started_at),
            "finished_at": _time(self.finished_at),
            "error": self.error,
            "stats": self.stats.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobRecord:
        submitted_at = _parse_time(data["submitted_at"])
        if submitted_at is None:
            raise ValueError("submitted_at is required")
        return cls(
            id=data["id"],
            url=data["url"],
            limits=JobLimits.from_dict(data["limits"]),
            status=JobStatus(data["status"]),
            submitted_at=submitted_at,
            started_at=_parse_time(data.get("started_at")),
            finished_at=_parse_time(data.get("finished_at")),
            error=data.get("error"),
            stats=JobStats.from_dict(data.get("stats", {})),
        )


class DaemonError(Exception):
    """An error reported to clients, identified by its ``code``."""

    code = "internal"


class InvalidRequestError(DaemonError, ValueError):
    code = "invalid_request"


class UnauthorizedError(DaemonError):
    code = "unauthorized"


class NotFoundError(DaemonError, LookupError):
    code = "not_found"


class ConflictError(DaemonError):
    code = "conflict"


class InternalError(DaemonError):
    code = "internal"


ERRORS_BY_CODE: dict[str, type[DaemonError]] = {
    cls.code: cls
    for cls in (InvalidRequestError, UnauthorizedError, NotFoundError, ConflictError, InternalError)
}
