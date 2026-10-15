"""``crawld start`` and ``crawld stop`` with a real background daemon process."""

import socket
from pathlib import Path

import pytest

from crawl_daemon.cli import EXIT_FAILED, EXIT_NOT_RUNNING, EXIT_OK, main
from crawl_daemon.state import LOG_FILE, pid_alive, read_state


def crawld(capsys: pytest.CaptureFixture[str], data_dir: Path, *args: str) -> tuple[int, str, str]:
    capsys.readouterr()
    code = main([*args, "--data-dir", str(data_dir)])
    out, err = capsys.readouterr()
    return code, out, err


def test_start_ping_stop(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = crawld(capsys, tmp_path, "start", "--port", "0")
    assert code == EXIT_OK, err
    state = read_state(tmp_path)
    assert state is not None
    try:
        assert out.strip() == f"crawld started (pid {state.pid}, port {state.port})"
        assert pid_alive(state.pid)
        assert crawld(capsys, tmp_path, "ping")[0] == EXIT_OK

        code, out, _ = crawld(capsys, tmp_path, "start", "--port", "0")
        assert (code, out.strip()) == (
            EXIT_OK,
            f"crawld is already running (pid {state.pid}, port {state.port})",
        )
        assert read_state(tmp_path) == state  # no second daemon
    finally:
        code, out, err = crawld(capsys, tmp_path, "stop")
    assert (code, out.strip()) == (EXIT_OK, "crawld stopped"), err
    assert not pid_alive(state.pid)
    assert read_state(tmp_path) is None
    assert crawld(capsys, tmp_path, "ping")[0] == EXIT_NOT_RUNNING
    assert "listening on 127.0.0.1" in (tmp_path / LOG_FILE).read_text()


def test_start_fails_on_a_taken_port(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        port = taken.getsockname()[1]
        code, _, err = crawld(capsys, tmp_path, "start", "--port", str(port))
    assert code == EXIT_FAILED
    assert "did not start" in err
    assert f"cannot listen on 127.0.0.1:{port}" in err
    assert read_state(tmp_path) is None


def test_start_fails_on_bad_database(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = crawld(capsys, tmp_path, "start", "--port", "0", "--database", "mysql://x/y")
    assert code == EXIT_FAILED
    assert "unsupported database URL scheme 'mysql'" in err
