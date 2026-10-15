import sys
from pathlib import Path

import pytest

from crawl_daemon.storage import StorageError, open_storage
from crawl_daemon.storage.sqlite import SqliteStorage


def test_default_is_sqlite_in_data_dir(tmp_path: Path) -> None:
    storage = open_storage("", tmp_path)
    assert isinstance(storage, SqliteStorage)
    assert storage.path == tmp_path / "crawld.db"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("sqlite:///crawls.db", Path("crawls.db")),
        ("sqlite:////var/lib/crawld.db", Path("/var/lib/crawld.db")),
        ("SQLITE:///C:/data/crawld.db", Path("C:/data/crawld.db")),
    ],
)
def test_sqlite_url(url: str, expected: Path, tmp_path: Path) -> None:
    storage = open_storage(url, tmp_path)
    assert isinstance(storage, SqliteStorage)
    assert storage.path == expected


@pytest.mark.parametrize("url", ["sqlite:///", "sqlite://crawls.db", "sqlite:crawls.db"])
def test_malformed_sqlite_url(url: str, tmp_path: Path) -> None:
    with pytest.raises(StorageError, match=r"sqlite:///PATH"):
        open_storage(url, tmp_path)


@pytest.mark.parametrize("url", ["postgresql://user@localhost/crawls", "postgres://localhost/x"])
def test_postgres_url(url: str, tmp_path: Path) -> None:
    pytest.importorskip("psycopg", reason="needs the postgres extra")
    from crawl_daemon.storage.postgres import PostgresStorage

    assert isinstance(open_storage(url, tmp_path), PostgresStorage)


def test_postgres_without_driver(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(sys.modules, "crawl_daemon.storage.postgres", raising=False)
    monkeypatch.setitem(sys.modules, "psycopg", None)  # makes ``import psycopg`` fail
    with pytest.raises(StorageError, match=r"crawl-daemon\[postgres\]"):
        open_storage("postgresql://localhost/crawls", tmp_path)


@pytest.mark.parametrize("url", ["mysql://localhost/crawls", "crawls.db", "http://x/"])
def test_unsupported_scheme(url: str, tmp_path: Path) -> None:
    with pytest.raises(StorageError, match="sqlite:///PATH or postgresql://"):
        open_storage(url, tmp_path)


async def test_unreachable_postgres(tmp_path: Path) -> None:
    pytest.importorskip("psycopg", reason="needs the postgres extra")
    storage = open_storage("postgresql://nobody@127.0.0.1:1/none?connect_timeout=1", tmp_path)
    with pytest.raises(StorageError, match="cannot connect to PostgreSQL"):
        await storage.open()
