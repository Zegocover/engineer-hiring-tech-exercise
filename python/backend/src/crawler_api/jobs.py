"""Crawl jobs and where they are kept."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from site_crawler.models import CrawlConfig, CrawlStats, PageResult


class JobStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(eq=False, slots=True)
class CrawlJob:
    """One crawl and everything it has produced so far.

    ``stats`` is the crawler's live statistics object, so it is current while
    the crawl runs. ``links`` holds each distinct link in first-seen order and
    ``link_set`` makes the membership check cheap.
    """

    id: str
    config: CrawlConfig
    status: JobStatus = JobStatus.RUNNING
    started_at: datetime = field(default_factory=utcnow)
    finished_at: datetime | None = None
    pages: list[PageResult] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    link_set: set[str] = field(default_factory=set)
    stats: CrawlStats = field(default_factory=CrawlStats)
    error: str | None = None
    task: asyncio.Task[None] | None = field(default=None, repr=False)


class JobStore(Protocol):
    def add(self, job: CrawlJob) -> None: ...

    def get(self, job_id: str) -> CrawlJob | None: ...

    def list_recent_first(self) -> list[CrawlJob]: ...


class InMemoryJobStore:
    """Jobs held in process memory, in the order they were started."""

    def __init__(self) -> None:
        self._jobs: dict[str, CrawlJob] = {}

    def add(self, job: CrawlJob) -> None:
        self._jobs[job.id] = job

    def get(self, job_id: str) -> CrawlJob | None:
        return self._jobs.get(job_id)

    def list_recent_first(self) -> list[CrawlJob]:
        return list(reversed(self._jobs.values()))
