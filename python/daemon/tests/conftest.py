import asyncio
import os
import sys
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from pathlib import Path

import pytest

from crawl_daemon.storage import Storage, open_storage

POSTGRES_URL = os.environ.get("CRAWLD_TEST_POSTGRES_URL", "")
needs_postgres = pytest.mark.skipif(
    not POSTGRES_URL, reason="set CRAWLD_TEST_POSTGRES_URL to run PostgreSQL tests"
)

StorageOpener = Callable[[], Awaitable[Storage]]


def pytest_asyncio_loop_factories(
    config: pytest.Config, item: pytest.Item
) -> Mapping[str, Callable[[], asyncio.AbstractEventLoop]]:
    # psycopg's async mode can't use the Proactor loop, Windows' default; the daemon
    # runs on a selector loop there too.
    if sys.platform == "win32":
        return {"selector": asyncio.SelectorEventLoop}
    return {"default": asyncio.new_event_loop}


async def reset_postgres() -> None:
    """Drop the daemon's tables so each test starts from an empty database."""
    import psycopg

    async with await psycopg.AsyncConnection.connect(POSTGRES_URL, autocommit=True) as conn:
        await conn.execute("DROP TABLE IF EXISTS parse_cache, links, pages, jobs, meta CASCADE")


def database_url(kind: str, tmp_path: Path) -> str:
    if kind == "sqlite":
        return f"sqlite:///{tmp_path / 'crawld.db'}"
    if not POSTGRES_URL:
        pytest.skip("set CRAWLD_TEST_POSTGRES_URL to run PostgreSQL tests")
    return POSTGRES_URL


@pytest.fixture(params=["sqlite", pytest.param("postgres", marks=needs_postgres)])
async def db_url(request: pytest.FixtureRequest, tmp_path: Path) -> str:
    """A database URL for an empty database, once per supported database."""
    url = database_url(request.param, tmp_path)
    if request.param == "postgres":
        await reset_postgres()
    return url


@pytest.fixture
async def open_db(db_url: str, tmp_path: Path) -> AsyncIterator[StorageOpener]:
    """Opens storages on the test database; all are closed after the test."""
    opened: list[Storage] = []

    async def opener() -> Storage:
        storage = open_storage(db_url, tmp_path)
        await storage.open()
        opened.append(storage)
        return storage

    yield opener
    for storage in opened:
        await storage.aclose()


@pytest.fixture
async def storage(open_db: StorageOpener) -> Storage:
    return await open_db()
