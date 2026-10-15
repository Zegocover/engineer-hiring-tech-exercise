"""A small blocking client for the daemon, used by the ``crawld`` command.

Each call opens a connection, sends one request and reads one response. The
daemon is found through the state file in its data directory.
"""

from __future__ import annotations

import socket
from pathlib import Path
from typing import Any

from crawl_daemon.models import UnauthorizedError
from crawl_daemon.protocol import Request, decode_response, encode_request
from crawl_daemon.server import HOST
from crawl_daemon.state import DaemonState, read_state


class DaemonNotRunningError(Exception):
    """No daemon is answering for the data directory."""


class DaemonClient:
    def __init__(self, data_dir: Path, *, timeout: float = 60.0) -> None:
        self.data_dir = data_dir
        self.timeout = timeout

    def state(self) -> DaemonState:
        state = read_state(self.data_dir)
        if state is None:
            raise DaemonNotRunningError(f"the daemon is not running (data dir {self.data_dir})")
        return state

    def call(self, op: str, **args: Any) -> Any:
        """Send one request; return its result or raise the daemon's error."""
        return call_daemon(self.state(), op, args, timeout=self.timeout)

    def ping(self) -> dict[str, Any] | None:
        """The daemon's ping reply, or ``None`` if it is not running."""
        try:
            result: dict[str, Any] = self.call("ping")
        except DaemonNotRunningError:
            return None
        return result


def call_daemon(state: DaemonState, op: str, args: dict[str, Any], *, timeout: float = 60.0) -> Any:
    try:
        sock = socket.create_connection((HOST, state.port), timeout=timeout)
    except OSError as exc:
        raise DaemonNotRunningError(
            f"the daemon is not running (nothing answers on port {state.port})"
        ) from exc
    with sock, sock.makefile("rb") as replies:
        try:
            sock.sendall(encode_request(Request(op, state.token, args)))
            line = replies.readline()
        except OSError as exc:
            raise DaemonNotRunningError(f"lost the connection to the daemon: {exc}") from exc
    if not line:
        raise DaemonNotRunningError("the daemon closed the connection without answering")
    try:
        return decode_response(line)
    except UnauthorizedError as exc:
        # Something else now owns the port the state file names.
        raise DaemonNotRunningError(
            "the daemon is not running (its state file is out of date)"
        ) from exc
