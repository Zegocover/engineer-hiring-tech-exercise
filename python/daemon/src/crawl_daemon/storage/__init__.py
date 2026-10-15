"""Where jobs, their results and the parse cache are kept.

:func:`open_storage` picks the database from a URL: SQLite (the default,
standard library only) or PostgreSQL (the ``postgres`` extra).
"""

from __future__ import annotations

import importlib
from pathlib import Path

from crawl_daemon.storage.base import Storage, StorageError

DEFAULT_DATABASE_FILE = "crawld.db"
POSTGRES_HINT = (
    "install it with: pip install 'crawl-daemon[postgres]' (or uv sync --extra postgres)"
)


def open_storage(database_url: str, data_dir: Path) -> Storage:
    """Create (but don't open) the storage ``database_url`` names.

    An empty URL means ``crawld.db`` in ``data_dir``. ``sqlite:///PATH`` takes
    everything after the three slashes as the path, relative or absolute.
    """
    if not database_url:
        from crawl_daemon.storage.sqlite import SqliteStorage

        return SqliteStorage(data_dir / DEFAULT_DATABASE_FILE)

    scheme = database_url.partition(":")[0].lower()
    if scheme == "sqlite":
        prefix = "sqlite:///"
        path = database_url[len(prefix) :]
        if not database_url.lower().startswith(prefix) or not path:
            raise StorageError("a SQLite URL looks like sqlite:///PATH")
        from crawl_daemon.storage.sqlite import SqliteStorage

        return SqliteStorage(Path(path))
    if scheme in ("postgresql", "postgres"):
        try:
            module = importlib.import_module("crawl_daemon.storage.postgres")
        except ImportError as exc:
            raise StorageError(
                f"PostgreSQL support is not installed ({exc.name or exc}); {POSTGRES_HINT}"
            ) from exc
        storage: Storage = module.PostgresStorage(database_url)
        return storage
    raise StorageError(
        f"unsupported database URL scheme {scheme!r}: use sqlite:///PATH or postgresql://..."
    )


__all__ = ["Storage", "StorageError", "open_storage"]
