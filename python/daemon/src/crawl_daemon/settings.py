"""Daemon-wide settings, read from ``CRAWLD_*`` environment variables."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields
from pathlib import Path

from site_crawler.models import DEFAULT_USER_AGENT

ENV_PREFIX = "CRAWLD_"
DEFAULT_PORT = 8765


def _parse_bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"not a boolean: {raw!r}")


# Field annotations are strings under ``from __future__ import annotations``.
_PARSERS: dict[str, Callable[[str], object]] = {
    "int": int,
    "float": float,
    "str": str,
    "bool": _parse_bool,
}


@dataclass(frozen=True, slots=True)
class Settings:
    default_max_pages: int = 1000
    """Page budget for a job that does not set one."""
    max_pages_limit: int = 10_000
    """Largest page budget a job may ask for."""
    default_concurrency: int = 8
    max_concurrency: int = 32
    max_parallel_jobs: int = 2
    """Jobs running at once; the rest wait as ``queued``."""
    parse_cache: bool = True
    """Reuse links parsed from identical pages, across jobs and restarts."""
    max_connections: int = 100
    """HTTP connections shared by all jobs."""
    request_timeout: float = 10.0
    user_agent: str = DEFAULT_USER_AGENT
    port: int = DEFAULT_PORT
    """Loopback port to listen on; 0 picks a free one."""
    data_dir: str = ""
    """Where the state file, log and default database live; empty means the per-user default."""
    database_url: str = ""
    """``sqlite:///PATH`` or ``postgresql://...``; empty means ``crawld.db`` in the data dir."""

    def __post_init__(self) -> None:
        for name in (
            "default_max_pages",
            "max_pages_limit",
            "default_concurrency",
            "max_concurrency",
            "max_parallel_jobs",
            "max_connections",
        ):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be at least 1")
        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be positive")
        if not 0 <= self.port <= 65535:
            raise ValueError("port must be between 0 and 65535")

    @property
    def resolved_data_dir(self) -> Path:
        return Path(self.data_dir) if self.data_dir else default_data_dir()

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Build settings, overriding defaults with ``CRAWLD_<FIELD>`` variables."""
        env = os.environ if environ is None else environ
        overrides: dict[str, object] = {}
        for f in fields(cls):
            raw = env.get(ENV_PREFIX + f.name.upper())
            if raw is None:
                continue
            try:
                overrides[f.name] = _PARSERS[str(f.type)](raw)
            except ValueError as exc:
                raise ValueError(f"{ENV_PREFIX}{f.name.upper()}: invalid value {raw!r}") from exc
        return cls(**overrides)  # type: ignore[arg-type]


def default_data_dir(
    platform: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """The per-user directory for the daemon's state file, log and database.

    ``CRAWLD_DATA_DIR`` wins; otherwise ``%LOCALAPPDATA%\\crawld`` on Windows,
    ``~/Library/Application Support/crawld`` on macOS and
    ``$XDG_STATE_HOME/crawld`` (default ``~/.local/state/crawld``) elsewhere.
    """
    platform = sys.platform if platform is None else platform
    env = os.environ if environ is None else environ
    home = Path.home() if home is None else home
    if env.get("CRAWLD_DATA_DIR"):
        return Path(env["CRAWLD_DATA_DIR"])
    if platform == "win32":
        local = env.get("LOCALAPPDATA")
        base = Path(local) if local else home / "AppData" / "Local"
    elif platform == "darwin":
        base = home / "Library" / "Application Support"
    else:
        state = env.get("XDG_STATE_HOME")
        base = Path(state) if state else home / ".local" / "state"
    return base / "crawld"
