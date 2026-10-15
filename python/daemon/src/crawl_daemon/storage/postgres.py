"""PostgreSQL storage on a small ``psycopg`` connection pool.

Importing this module needs the ``postgres`` extra. psycopg's async mode
cannot run on Windows' default Proactor event loop; the daemon runs on a
selector loop there (see :mod:`crawl_daemon.server`).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from crawl_daemon.storage.base import StorageError
from crawl_daemon.storage.sql import Row, SqlStorage, WriteOp


def _sql(statement: str) -> str:
    """Our queries use ``?``; psycopg wants ``%s``. No query contains a literal ``?`` or ``%``."""
    return statement.replace("?", "%s")


class PostgresStorage(SqlStorage):
    DDL = (
        """CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            limits JSONB NOT NULL,
            status TEXT NOT NULL,
            submitted_at TIMESTAMPTZ NOT NULL,
            started_at TIMESTAMPTZ,
            finished_at TIMESTAMPTZ,
            error TEXT,
            pages BIGINT NOT NULL DEFAULT 0,
            fetched BIGINT NOT NULL DEFAULT 0,
            errors BIGINT NOT NULL DEFAULT 0,
            robots_skipped BIGINT NOT NULL DEFAULT 0,
            parse_cache_hits BIGINT NOT NULL DEFAULT 0
        )""",
        "CREATE INDEX IF NOT EXISTS jobs_by_submitted ON jobs (submitted_at)",
        "CREATE INDEX IF NOT EXISTS jobs_by_status ON jobs (status)",
        """CREATE TABLE IF NOT EXISTS pages (
            job_id TEXT NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
            seq BIGINT NOT NULL,
            url TEXT NOT NULL,
            links JSONB NOT NULL,
            PRIMARY KEY (job_id, seq)
        )""",
        """CREATE TABLE IF NOT EXISTS links (
            job_id TEXT NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
            seq BIGINT NOT NULL,
            url TEXT NOT NULL,
            PRIMARY KEY (job_id, seq)
        )""",
        # On md5(url): a btree entry can't hold an arbitrarily long URL.
        "CREATE UNIQUE INDEX IF NOT EXISTS links_distinct ON links (job_id, md5(url))",
        """CREATE TABLE IF NOT EXISTS parse_cache (
            key TEXT PRIMARY KEY,
            links JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL
        )""",
    )

    def __init__(self, conninfo: str) -> None:
        self._conninfo = conninfo
        self._pool: AsyncConnectionPool | None = None

    async def _connect(self) -> None:
        pool = AsyncConnectionPool(self._conninfo, min_size=1, max_size=4, open=False)
        try:
            await pool.open(wait=True, timeout=10)
        except (PoolTimeout, psycopg.Error) as exc:
            await pool.close()
            raise StorageError(f"cannot connect to PostgreSQL: {exc}") from exc
        self._pool = pool

    async def aclose(self) -> None:
        pool, self._pool = self._pool, None
        if pool is not None:
            await pool.close()

    def _ready_pool(self) -> AsyncConnectionPool:
        if self._pool is None:
            raise StorageError("the database is closed")
        return self._pool

    async def _read(self, sql: str, params: Sequence[Any] = ()) -> list[Row]:
        async with self._ready_pool().connection() as conn:
            cursor = await conn.execute(_sql(sql), tuple(params))
            return await cursor.fetchall()

    async def _write(self, ops: Sequence[WriteOp]) -> None:
        async with (
            self._ready_pool().connection() as conn,
            conn.transaction(),
            conn.cursor() as cursor,
        ):
            for sql, rows in ops:
                if len(rows) == 1:
                    await cursor.execute(_sql(sql), tuple(rows[0]))
                else:
                    await cursor.executemany(_sql(sql), rows)

    def _encode_time(self, value: datetime | None) -> Any:
        return value

    def _decode_time(self, value: Any) -> datetime | None:
        return None if value is None else value.astimezone(UTC)

    def _encode_json(self, value: Any) -> Any:
        return Jsonb(value)

    def _decode_json(self, value: Any) -> Any:
        return value  # psycopg decodes jsonb
