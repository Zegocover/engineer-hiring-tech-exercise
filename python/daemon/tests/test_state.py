import os
import stat
import sys
from pathlib import Path

import pytest

from crawl_daemon.state import (
    DaemonState,
    pid_alive,
    read_state,
    remove_state,
    state_path,
    write_state,
)

STATE = DaemonState(pid=123, port=8765, token="secret", started_at="2026-10-15T00:00:00+00:00")


def test_round_trip(tmp_path: Path) -> None:
    write_state(tmp_path, STATE)
    assert read_state(tmp_path) == STATE
    assert list(tmp_path.iterdir()) == [state_path(tmp_path)]  # no temp file left behind


def test_creates_data_dir(tmp_path: Path) -> None:
    write_state(tmp_path / "new" / "dir", STATE)
    assert read_state(tmp_path / "new" / "dir") == STATE


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
def test_owner_only(tmp_path: Path) -> None:
    write_state(tmp_path, STATE)
    assert stat.S_IMODE(state_path(tmp_path).stat().st_mode) == 0o600


@pytest.mark.parametrize("content", ["", "not json", '{"pid": 1}', '{"pid": "x", "port": 1}'])
def test_unreadable_is_none(tmp_path: Path, content: str) -> None:
    state_path(tmp_path).write_text(content)
    assert read_state(tmp_path) is None


def test_missing_is_none(tmp_path: Path) -> None:
    assert read_state(tmp_path) is None


def test_remove_only_our_own(tmp_path: Path) -> None:
    write_state(tmp_path, STATE)
    remove_state(tmp_path, "someone else's token")
    assert read_state(tmp_path) == STATE
    remove_state(tmp_path, "secret")
    assert not state_path(tmp_path).exists()
    remove_state(tmp_path, "secret")  # already gone: fine


def test_pid_alive() -> None:
    assert pid_alive(os.getpid())
    assert not pid_alive(0)
    assert not pid_alive(2**22 + 12345)  # far above any real pid
