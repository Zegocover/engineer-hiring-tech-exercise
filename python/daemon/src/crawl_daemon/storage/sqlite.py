"""SQLite storage: one file, one connection, one thread.

``sqlite3`` connections belong to the thread that uses them, and SQLite
serialises writes anyway, so every call runs on a dedicated single-thread
executor. That keeps the event loop free without an extra dependency.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from crawl_daemon.storage.base import StorageError
from crawl_daemon.storage.sql import Row, SqlStorage, WriteOp


class SqliteStorage(SqlStorage):
    DDL = (
        """CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            limits TEXT NOT NULL,
            status TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            error TEXT,
            pages INTEGER NOT NULL DEFAULT 0,
            fetched INTEGER NOT NULL DEFAULT 0,
            errors INTEGER NOT NULL DEFAULT 0,
            robots_skipped INTEGER NOT NULL DEFAULT 0,
            parse_cache_hits INTEGER NOT NULL DEFAULT 0
        )""",
        "CREATE INDEX IF NOT EXISTS jobs_by_submitted ON jobs (submitted_at)",
        "CREATE INDEX IF NOT EXISTS jobs_by_status ON jobs (status)",
        """CREATE TABLE IF NOT EXISTS pages (
            job_id TEXT NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
            seq INTEGER NOT NULL,
            url TEXT NOT NULL,
            links TEXT NOT NULL,
            PRIMARY KEY (job_id, seq)
        )""",
        """CREATE TABLE IF NOT EXISTS links (
            job_id TEXT NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
            seq INTEGER NOT NULL,
            url TEXT NOT NULL,
            PRIMARY KEY (job_id, seq),
            UNIQUE (job_id, url)
        )""",
        """CREATE TABLE IF NOT EXISTS parse_cache (
            key TEXT PRIMARY KEY,
            links TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""",
    )

    def __init__(self, path: Path) -> None:
        self.path = path
        self._executor: ThreadPoolExecutor | None = None
        self._conn: sqlite3.Connection | None = None

    async def _connect(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="crawld-sqlite")
        try:
            self._conn = await self._call(self._open_connection)
        except (OSError, sqlite3.Error) as exc:
            await self.aclose()
            raise StorageError(f"cannot open SQLite database {self.path}: {exc}") from exc

    def _open_connection(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    async def aclose(self) -> None:
        executor, self._executor = self._executor, None
        conn, self._conn = self._conn, None
        if executor is None:
            return
        if conn is not None:
            await asyncio.get_running_loop().run_in_executor(executor, conn.close)
        executor.shutdown(wait=True)

    async def _call[T](self, fn: Callable[..., T], *args: Any) -> T:
        if self._executor is None:
            raise StorageError("the database is closed")
        return await asyncio.get_running_loop().run_in_executor(self._executor, fn, *args)

    async def _read(self, sql: str, params: Sequence[Any] = ()) -> list[Row]:
        return await self._call(self._read_sync, sql, tuple(params))

    def _read_sync(self, sql: str, params: tuple[Any, ...]) -> list[Row]:
        assert self._conn is not None
        return self._conn.execute(sql, params).fetchall()

    async def _write(self, ops: Sequence[WriteOp]) -> None:
        await self._call(self._write_sync, ops)

    def _write_sync(self, ops: Sequence[WriteOp]) -> None:
        assert self._conn is not None
        with self._conn:  # commits, or rolls back on error
            for sql, rows in ops:
                if len(rows) == 1:
                    self._conn.execute(sql, tuple(rows[0]))
                else:
                    self._conn.executemany(sql, rows)

    # Times are UTC ISO-8601 text with a fixed width, so text order is time order.
    def _encode_time(self, value: datetime | None) -> Any:
        return None if value is None else value.astimezone(UTC).isoformat(timespec="microseconds")

    def _decode_time(self, value: Any) -> datetime | None:
        return None if value is None else datetime.fromisoformat(value)

    def _encode_json(self, value: Any) -> Any:
        return json.dumps(value, separators=(",", ":"))

    def _decode_json(self, value: Any) -> Any:
        return json.loads(value)
