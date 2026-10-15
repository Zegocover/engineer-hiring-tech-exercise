"""The daemon over real loopback sockets, in this process, with in-memory sites."""

import asyncio
import json
import socket
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest
from site_crawler.interfaces import Fetcher

from crawl_daemon.protocol import MAX_LINE_BYTES
from crawl_daemon.server import DaemonStartError, run_daemon
from crawl_daemon.settings import Settings
from crawl_daemon.state import DaemonState, read_state, state_path, write_state
from tests.fakes import BASE, FakeSite


@asynccontextmanager
async def running_daemon(
    data_dir: Path, site: Fetcher | None = None, **settings: Any
) -> AsyncIterator[tuple[DaemonState, asyncio.Task[None]]]:
    """Run the daemon in a task until the block ends."""
    ready: asyncio.Future[DaemonState] = asyncio.get_running_loop().create_future()
    fetcher = site or FakeSite({})
    task = asyncio.create_task(
        run_daemon(
            Settings(data_dir=str(data_dir), port=0, **settings),
            fetcher_factory=lambda: fetcher,
            on_ready=ready.set_result,
            flush_interval=0.01,
        )
    )
    waiters: list[asyncio.Future[Any]] = [ready, task]
    done, _ = await asyncio.wait(waiters, timeout=10, return_when=asyncio.FIRST_COMPLETED)
    if task in done:
        task.result()  # raise the startup error
    state = ready.result()
    try:
        yield state, task
    finally:
        if not task.done():
            await raw_call(state, {"op": "shutdown", "token": state.token})
        async with asyncio.timeout(10):
            await task


async def send_lines(port: int, *lines: bytes) -> list[dict[str, Any]]:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    try:
        replies = []
        for line in lines:
            writer.write(line)
            await writer.drain()
            reply = await reader.readline()
            if not reply:
                break
            replies.append(json.loads(reply))
        return replies
    finally:
        writer.close()


async def raw_call(state: DaemonState, request: dict[str, Any]) -> dict[str, Any]:
    (reply,) = await send_lines(state.port, json.dumps(request).encode() + b"\n")
    return reply


Caller = Callable[..., Awaitable[dict[str, Any]]]


def caller(state: DaemonState) -> Caller:
    async def call(op: str, **args: Any) -> dict[str, Any]:
        return await raw_call(state, {"op": op, "token": state.token, "args": args})

    return call


@pytest.fixture
async def daemon(tmp_path: Path) -> AsyncIterator[DaemonState]:
    site = FakeSite({BASE: ["/a"], BASE + "a": []})
    async with running_daemon(tmp_path, site) as (state, _):
        yield state


# --- listening -------------------------------------------------------------------------


async def test_state_file_names_port_pid_and_token(daemon: DaemonState, tmp_path: Path) -> None:
    import os

    assert read_state(tmp_path) == daemon
    assert daemon.pid == os.getpid()
    assert len(daemon.token) >= 32
    reply = await caller(daemon)("ping")
    assert reply["result"]["port"] == daemon.port
    assert (reply["result"]["running_jobs"], reply["result"]["queued_jobs"]) == (0, 0)


async def test_port_in_use(tmp_path: Path) -> None:
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        port = taken.getsockname()[1]
        with pytest.raises(DaemonStartError, match=f"127.0.0.1:{port}"):
            await run_daemon(Settings(data_dir=str(tmp_path), port=port))
    assert not state_path(tmp_path).exists()


async def test_second_daemon_refused(daemon: DaemonState, tmp_path: Path) -> None:
    with pytest.raises(DaemonStartError, match="already running"):
        await run_daemon(Settings(data_dir=str(tmp_path), port=0))
    assert (await caller(daemon)("ping"))["ok"]
    assert read_state(tmp_path) == daemon


async def test_stale_state_file_replaced(tmp_path: Path) -> None:
    with socket.socket() as probe:  # a port nobody is listening on
        probe.bind(("127.0.0.1", 0))
        free_port = probe.getsockname()[1]
    stale = DaemonState(pid=999_999, port=free_port, token="old", started_at="then")
    write_state(tmp_path, stale)
    async with running_daemon(tmp_path) as (state, _):
        assert read_state(tmp_path) == state
        assert state.token != "old"


async def test_shutdown_removes_state_file(tmp_path: Path) -> None:
    async with running_daemon(tmp_path) as (state, task):
        reply = await caller(state)("shutdown")
        assert reply == {"ok": True, "result": {"stopping": True}}
        async with asyncio.timeout(10):
            await task
    assert not state_path(tmp_path).exists()


# --- authentication --------------------------------------------------------------------


async def test_missing_token_rejected(daemon: DaemonState) -> None:
    reply = await raw_call(daemon, {"op": "submit", "args": {"url": BASE}})
    assert reply["error"]["code"] == "unauthorized"
    assert (await caller(daemon)("list"))["result"] == []


async def test_token_from_previous_run_rejected(tmp_path: Path) -> None:
    async with running_daemon(tmp_path) as (first, _):
        pass
    async with running_daemon(tmp_path) as (second, _):
        reply = await raw_call(second, {"op": "ping", "token": first.token})
        assert reply["error"]["code"] == "unauthorized"


# --- operations ------------------------------------------------------------------------


async def test_submit_and_read_back(daemon: DaemonState) -> None:
    call = caller(daemon)
    submitted = (await call("submit", url=BASE, max_depth=1))["result"]
    assert submitted["status"] in ("queued", "running")
    assert submitted["limits"]["max_depth"] == 1
    job_id = submitted["id"]
    async with asyncio.timeout(5):
        while (await call("get", id=job_id))["result"]["status"] != "completed":  # noqa: ASYNC110
            await asyncio.sleep(0.01)
    pages = (await call("pages", id=job_id, offset=1, limit=1))["result"]
    assert pages == {
        "total": 2,
        "offset": 1,
        "limit": 1,
        "items": [{"url": BASE + "a", "links": []}],
    }
    links = (await call("links", id=job_id))["result"]
    assert (links["total"], links["items"]) == (1, [BASE + "a"])
    listed = (await call("list", status="completed"))["result"]
    assert [job["id"] for job in listed] == [job_id]
    assert (await call("cancel", id=job_id))["error"]["code"] == "conflict"


@pytest.mark.parametrize(
    ("op", "args", "code"),
    [
        ("submit", {"url": "ftp://example.com/"}, "invalid_request"),
        ("submit", {"url": BASE, "max_depth": -1}, "invalid_request"),
        ("submit", {"url": BASE, "max_pages": "lots"}, "invalid_request"),
        ("submit", {"url": BASE, "allowed_hosts": "x"}, "invalid_request"),
        ("submit", {"url": BASE, "colour": "red"}, "invalid_request"),
        ("get", {"id": "nope"}, "not_found"),
        ("pages", {"id": "nope"}, "not_found"),
        ("links", {"id": "nope", "limit": 0}, "invalid_request"),
        ("list", {"status": "sleeping"}, "invalid_request"),
        ("cancel", {}, "invalid_request"),
    ],
)
async def test_errors(daemon: DaemonState, op: str, args: dict[str, Any], code: str) -> None:
    reply = await caller(daemon)(op, **args)
    assert reply["ok"] is False
    assert reply["error"]["code"] == code
    assert (await caller(daemon)("list"))["result"] == []


# --- misbehaving clients ---------------------------------------------------------------


async def test_unknown_operation(daemon: DaemonState) -> None:
    reply = await caller(daemon)("explode")
    assert reply["error"] == {"code": "invalid_request", "message": "unknown operation 'explode'"}
    assert (await caller(daemon)("ping"))["ok"]


async def test_malformed_line_keeps_connection(daemon: DaemonState) -> None:
    ping = json.dumps({"op": "ping", "token": daemon.token}).encode() + b"\n"
    replies = await send_lines(daemon.port, b"{nonsense\n", ping)
    assert replies[0]["error"]["code"] == "invalid_request"
    assert replies[1]["ok"] is True


async def test_oversized_request_closes_only_that_connection(daemon: DaemonState) -> None:
    reader, writer = await asyncio.open_connection("127.0.0.1", daemon.port)
    other_reader, other_writer = await asyncio.open_connection("127.0.0.1", daemon.port)
    try:
        writer.write(b"x" * (MAX_LINE_BYTES + 10))
        await writer.drain()
        reply = json.loads(await reader.readline())
        assert reply["error"]["code"] == "invalid_request"
        assert await reader.read() == b""  # closed

        other_writer.write(json.dumps({"op": "ping", "token": daemon.token}).encode() + b"\n")
        await other_writer.drain()
        assert json.loads(await other_reader.readline())["ok"] is True
    finally:
        writer.close()
        other_writer.close()


async def test_request_without_trailing_newline(daemon: DaemonState) -> None:
    reader, writer = await asyncio.open_connection("127.0.0.1", daemon.port)
    writer.write(json.dumps({"op": "ping", "token": daemon.token}).encode())
    writer.write_eof()
    reply = json.loads(await reader.readline())
    writer.close()
    assert reply["ok"] is True
