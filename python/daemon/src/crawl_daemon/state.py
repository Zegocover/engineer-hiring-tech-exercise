"""The state file a running daemon leaves in its data directory.

It tells clients the daemon's port and token, so they never need to be given
either. It is written atomically, readable only by its owner on POSIX, and
removed when the daemon stops cleanly.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

STATE_FILE = "crawld.json"
LOG_FILE = "crawld.log"


@dataclass(frozen=True, slots=True)
class DaemonState:
    pid: int
    port: int
    token: str
    started_at: str


def state_path(data_dir: Path) -> Path:
    return data_dir / STATE_FILE


def read_state(data_dir: Path) -> DaemonState | None:
    """The state file's contents, or ``None`` if it is missing or unreadable."""
    try:
        data = json.loads(state_path(data_dir).read_text(encoding="utf-8"))
        return DaemonState(
            pid=int(data["pid"]),
            port=int(data["port"]),
            token=str(data["token"]),
            started_at=str(data["started_at"]),
        )
    except (OSError, ValueError, KeyError, TypeError):
        return None


def write_state(data_dir: Path, state: DaemonState) -> None:
    """Replace the state file atomically, readable only by its owner."""
    data_dir.mkdir(parents=True, exist_ok=True)
    path = state_path(data_dir)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(asdict(state), file)
        os.replace(temp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            temp.unlink()
        raise


def remove_state(data_dir: Path, token: str) -> None:
    """Remove the state file if it is still ours (it holds ``token``)."""
    state = read_state(data_dir)
    if state is not None and state.token == token:
        with contextlib.suppress(FileNotFoundError):
            state_path(data_dir).unlink()


def pid_alive(pid: int) -> bool:
    """Whether a process with this id is running."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return bool(ok) and code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)  # signal 0 only checks; never use it on Windows, where it kills
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
