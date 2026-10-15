"""The storage interface every database implements."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from site_crawler.models import PageResult

from crawl_daemon.models import JobRecord, JobStats, JobStatus


class StorageError(Exception):
    """The database can't be used: bad URL, missing driver, unreachable or newer schema."""


class Storage(Protocol):
    """Jobs, their results and the parse cache, in one database."""

    async def open(self) -> None:
        """Connect, create missing tables and check the schema version."""
        ...

    async def aclose(self) -> None: ...

    async def create_job(self, job: JobRecord) -> None: ...

    async def update_job(self, job: JobRecord) -> None:
        """Save the job's status, times, error and statistics."""
        ...

    async def get_job(self, job_id: str) -> JobRecord | None: ...

    async def list_jobs(self, status: JobStatus | None = None) -> list[JobRecord]:
        """Jobs, most recently submitted first, optionally only those with ``status``."""
        ...

    async def append_results(
        self,
        job_id: str,
        pages: Sequence[tuple[int, PageResult]],
        links: Sequence[tuple[int, str]],
        stats: JobStats,
    ) -> None:
        """Store numbered pages and newly found distinct links, and the job's live statistics.

        All in one transaction. A link the job already has is ignored.
        """
        ...

    async def read_pages(
        self, job_id: str, offset: int, limit: int
    ) -> tuple[list[PageResult], int]:
        """A slice of the job's pages in report order, and how many it has in total."""
        ...

    async def read_links(self, job_id: str, offset: int, limit: int) -> tuple[list[str], int]:
        """A slice of the job's distinct links in first-found order, and the total."""
        ...

    async def mark_interrupted(self, error: str, at: datetime) -> int:
        """Fail every ``running`` job (left by a daemon that died); return how many."""
        ...

    async def get_parsed_links(self, keys: Sequence[str]) -> dict[str, list[str]]:
        """Cached parser output for whichever of ``keys`` are cached."""
        ...

    async def put_parsed_links(
        self, entries: Sequence[tuple[str, list[str]]], at: datetime
    ) -> None:
        """Cache parser output; a key that is already cached keeps its first entry."""
        ...
