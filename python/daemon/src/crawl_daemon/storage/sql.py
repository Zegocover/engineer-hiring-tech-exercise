"""SQL shared by the SQLite and PostgreSQL storages.

Queries are written once, with ``?`` placeholders. Each database supplies its
DDL, how to run statements, and how to encode times and JSON.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from site_crawler.models import PageResult

from crawl_daemon.models import JobLimits, JobRecord, JobStats, JobStatus
from crawl_daemon.storage.base import StorageError

SCHEMA_VERSION = 1

Row = tuple[Any, ...]
# A statement and the parameter rows to run it with, inside one transaction.
WriteOp = tuple[str, Sequence[Sequence[Any]]]

_JOB_COLUMNS = (
    "id, url, limits, status, submitted_at, started_at, finished_at, error, "
    "pages, fetched, errors, robots_skipped, parse_cache_hits"
)
_JOB_MARKS = ", ".join("?" * 13)
_STATS_SET = "pages = ?, fetched = ?, errors = ?, robots_skipped = ?, parse_cache_hits = ?"


def _stats_params(stats: JobStats) -> tuple[int, ...]:
    return (stats.pages, stats.fetched, stats.errors, stats.robots_skipped, stats.parse_cache_hits)


class SqlStorage(ABC):
    META_DDL = "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    DDL: tuple[str, ...] = ()

    # --- what each database provides -------------------------------------------------

    @abstractmethod
    async def _connect(self) -> None: ...

    @abstractmethod
    async def aclose(self) -> None: ...

    @abstractmethod
    async def _read(self, sql: str, params: Sequence[Any] = ()) -> list[Row]: ...

    @abstractmethod
    async def _write(self, ops: Sequence[WriteOp]) -> None:
        """Run every op in a single transaction."""

    @abstractmethod
    def _encode_time(self, value: datetime | None) -> Any: ...

    @abstractmethod
    def _decode_time(self, value: Any) -> datetime | None: ...

    @abstractmethod
    def _encode_json(self, value: Any) -> Any: ...

    @abstractmethod
    def _decode_json(self, value: Any) -> Any: ...

    # --- the Storage protocol ---------------------------------------------------------

    async def open(self) -> None:
        await self._connect()
        try:
            await self._ensure_schema()
        except BaseException:
            await self.aclose()
            raise

    async def _ensure_schema(self) -> None:
        await self._write([(self.META_DDL, [()])])
        rows = await self._read("SELECT value FROM meta WHERE key = ?", ("schema_version",))
        version = int(rows[0][0]) if rows else 0
        if version > SCHEMA_VERSION:
            raise StorageError(
                f"the database has schema version {version}, but this crawld supports "
                f"version {SCHEMA_VERSION} at most; upgrade crawld to use it"
            )
        ops: list[WriteOp] = [(ddl, [()]) for ddl in self.DDL]
        if version == 0:
            ops.append(
                (
                    "INSERT INTO meta (key, value) VALUES (?, ?)",
                    [("schema_version", str(SCHEMA_VERSION))],
                )
            )
        await self._write(ops)

    async def create_job(self, job: JobRecord) -> None:
        await self._write(
            [
                (
                    f"INSERT INTO jobs ({_JOB_COLUMNS}) VALUES ({_JOB_MARKS})",
                    [
                        (
                            job.id,
                            job.url,
                            self._encode_json(job.limits.to_dict()),
                            str(job.status),
                            self._encode_time(job.submitted_at),
                            self._encode_time(job.started_at),
                            self._encode_time(job.finished_at),
                            job.error,
                            *_stats_params(job.stats),
                        )
                    ],
                )
            ]
        )

    async def update_job(self, job: JobRecord) -> None:
        await self._write(
            [
                (
                    "UPDATE jobs SET status = ?, started_at = ?, finished_at = ?, error = ?, "
                    f"{_STATS_SET} WHERE id = ?",
                    [
                        (
                            str(job.status),
                            self._encode_time(job.started_at),
                            self._encode_time(job.finished_at),
                            job.error,
                            *_stats_params(job.stats),
                            job.id,
                        )
                    ],
                )
            ]
        )

    async def get_job(self, job_id: str) -> JobRecord | None:
        rows = await self._read(f"SELECT {_JOB_COLUMNS} FROM jobs WHERE id = ?", (job_id,))
        return self._job(rows[0]) if rows else None

    async def list_jobs(self, status: JobStatus | None = None) -> list[JobRecord]:
        order = "ORDER BY submitted_at DESC, id DESC"
        if status is None:
            rows = await self._read(f"SELECT {_JOB_COLUMNS} FROM jobs {order}")
        else:
            rows = await self._read(
                f"SELECT {_JOB_COLUMNS} FROM jobs WHERE status = ? {order}", (str(status),)
            )
        return [self._job(row) for row in rows]

    async def append_results(
        self,
        job_id: str,
        pages: Sequence[tuple[int, PageResult]],
        links: Sequence[tuple[int, str]],
        stats: JobStats,
    ) -> None:
        ops: list[WriteOp] = []
        if pages:
            ops.append(
                (
                    "INSERT INTO pages (job_id, seq, url, links) VALUES (?, ?, ?, ?)",
                    [
                        (job_id, seq, page.url, self._encode_json(list(page.links)))
                        for seq, page in pages
                    ],
                )
            )
        if links:
            ops.append(
                (
                    "INSERT INTO links (job_id, seq, url) VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
                    [(job_id, seq, url) for seq, url in links],
                )
            )
        stats_row = (*_stats_params(stats), job_id)
        ops.append((f"UPDATE jobs SET {_STATS_SET} WHERE id = ?", [stats_row]))
        await self._write(ops)

    async def read_pages(
        self, job_id: str, offset: int, limit: int
    ) -> tuple[list[PageResult], int]:
        rows = await self._read(
            "SELECT url, links FROM pages WHERE job_id = ? ORDER BY seq LIMIT ? OFFSET ?",
            (job_id, limit, offset),
        )
        total = await self._count("pages", job_id)
        return [PageResult(url, tuple(self._decode_json(links))) for url, links in rows], total

    async def read_links(self, job_id: str, offset: int, limit: int) -> tuple[list[str], int]:
        rows = await self._read(
            "SELECT url FROM links WHERE job_id = ? ORDER BY seq LIMIT ? OFFSET ?",
            (job_id, limit, offset),
        )
        total = await self._count("links", job_id)
        return [url for (url,) in rows], total

    async def _count(self, table: str, job_id: str) -> int:
        rows = await self._read(f"SELECT COUNT(*) FROM {table} WHERE job_id = ?", (job_id,))
        return int(rows[0][0])

    async def mark_interrupted(self, error: str, at: datetime) -> int:
        rows = await self._read("SELECT id FROM jobs WHERE status = ?", (str(JobStatus.RUNNING),))
        if rows:
            await self._write(
                [
                    (
                        "UPDATE jobs SET status = ?, error = ?, finished_at = ? WHERE id = ?",
                        [
                            (str(JobStatus.FAILED), error, self._encode_time(at), job_id)
                            for (job_id,) in rows
                        ],
                    )
                ]
            )
        return len(rows)

    async def get_parsed_links(self, keys: Sequence[str]) -> dict[str, list[str]]:
        if not keys:
            return {}
        marks = ", ".join("?" for _ in keys)
        rows = await self._read(
            f"SELECT key, links FROM parse_cache WHERE key IN ({marks})", tuple(keys)
        )
        return {key: list(self._decode_json(links)) for key, links in rows}

    async def put_parsed_links(
        self, entries: Sequence[tuple[str, list[str]]], at: datetime
    ) -> None:
        if not entries:
            return
        created = self._encode_time(at)
        await self._write(
            [
                (
                    "INSERT INTO parse_cache (key, links, created_at) VALUES (?, ?, ?) "
                    "ON CONFLICT (key) DO NOTHING",
                    [(key, self._encode_json(links), created) for key, links in entries],
                )
            ]
        )

    def _job(self, row: Row) -> JobRecord:
        (job_id, url, limits, status, submitted, started, finished, error, *stats) = row
        submitted_at = self._decode_time(submitted)
        if submitted_at is None:  # NOT NULL in the schema
            raise StorageError(f"job {job_id} has no submission time")
        return JobRecord(
            id=job_id,
            url=url,
            limits=JobLimits.from_dict(self._decode_json(limits)),
            status=JobStatus(status),
            submitted_at=submitted_at,
            started_at=self._decode_time(started),
            finished_at=self._decode_time(finished),
            error=error,
            stats=JobStats(*(int(value) for value in stats)),
        )
