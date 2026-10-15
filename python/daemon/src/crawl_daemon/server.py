"""The daemon: a loopback TCP server in front of the scheduler, and its lifecycle."""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import logging
import os
import secrets
import signal
import sys
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from site_crawler import DefaultHttpxFetcher

from crawl_daemon import __version__
from crawl_daemon.models import (
    DaemonError,
    InternalError,
    InvalidRequestError,
    JobStatus,
    UnauthorizedError,
    utcnow,
)
from crawl_daemon.protocol import (
    MAX_LINE_BYTES,
    Request,
    decode_request,
    decode_response,
    encode_error,
    encode_ok,
    encode_request,
)
from crawl_daemon.scheduler import FetcherFactory, JobScheduler
from crawl_daemon.settings import Settings
from crawl_daemon.state import DaemonState, read_state, remove_state, write_state
from crawl_daemon.storage import open_storage

logger = logging.getLogger(__name__)

HOST = "127.0.0.1"
MAX_SLICE = 1000
"""Most pages or links one request may ask for."""

Handler = Callable[[dict[str, Any]], Awaitable[Any]]


class DaemonStartError(Exception):
    """The daemon could not start: already running, port taken, or storage unusable."""


def loop_factory() -> asyncio.AbstractEventLoop:
    """The event loop the daemon runs on.

    A selector loop on Windows too: psycopg's async mode can't use the Proactor
    loop that is Windows' default.
    """
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop()
    return asyncio.new_event_loop()


# --- request arguments -----------------------------------------------------------------


def _check_keys(args: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(args) - allowed)
    if unknown:
        raise InvalidRequestError(f"unknown argument(s): {', '.join(unknown)}")


def _str(args: dict[str, Any], name: str) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value:
        raise InvalidRequestError(f"'{name}' must be a non-empty string")
    return value


def _opt_int(args: dict[str, Any], name: str) -> int | None:
    value = args.get(name)
    if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
        raise InvalidRequestError(f"'{name}' must be an integer")
    return value


def _bool(args: dict[str, Any], name: str, default: bool) -> bool:
    value = args.get(name, default)
    if not isinstance(value, bool):
        raise InvalidRequestError(f"'{name}' must be true or false")
    return value


def _str_list(args: dict[str, Any], name: str) -> list[str]:
    value = args.get(name, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise InvalidRequestError(f"'{name}' must be a list of strings")
    return value


def _slice(args: dict[str, Any]) -> tuple[int, int]:
    offset = _opt_int(args, "offset")
    limit = _opt_int(args, "limit")
    offset = 0 if offset is None else offset
    limit = 100 if limit is None else limit
    if offset < 0:
        raise InvalidRequestError("'offset' must not be negative")
    if not 1 <= limit <= MAX_SLICE:
        raise InvalidRequestError(f"'limit' must be between 1 and {MAX_SLICE}")
    return offset, limit


# --- the server ------------------------------------------------------------------------


class DaemonServer:
    """Serves JSON-line requests on ``127.0.0.1``; every request must carry ``token``.

    Each connection is served on its own, so a misbehaving client only ever
    loses its own connection.
    """

    def __init__(self, scheduler: JobScheduler, token: str, *, port: int = 0) -> None:
        self._scheduler = scheduler
        self._token = token.encode()
        self._port = port
        self._server: asyncio.Server | None = None
        self._connections: set[asyncio.StreamWriter] = set()
        self._ready = asyncio.Event()
        self._stop = asyncio.Event()
        self._handlers: dict[str, Handler] = {
            "ping": self._ping,
            "submit": self._submit,
            "get": self._get,
            "list": self._list,
            "pages": self._pages,
            "links": self._links,
            "cancel": self._cancel,
            "shutdown": self._shutdown,
        }

    @property
    def port(self) -> int:
        return self._port

    async def start(self) -> int:
        """Start listening; returns the port. Requests wait until :meth:`set_ready`."""
        self._server = await asyncio.start_server(
            self._handle, HOST, self._port, limit=MAX_LINE_BYTES
        )
        self._port = self._server.sockets[0].getsockname()[1]
        return self._port

    def set_ready(self) -> None:
        self._ready.set()

    def request_stop(self) -> None:
        self._stop.set()

    async def wait_stopped(self) -> None:
        await self._stop.wait()

    async def close(self) -> None:
        """Stop listening and drop every connection."""
        server, self._server = self._server, None
        if server is None:
            return
        server.close()
        for writer in list(self._connections):
            writer.close()
        with contextlib.suppress(Exception):
            await server.wait_closed()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._connections.add(writer)
        try:
            while True:
                try:
                    line = await reader.readuntil(b"\n")
                except asyncio.IncompleteReadError as exc:
                    if not exc.partial.strip():
                        break
                    line = exc.partial  # a last request without a newline
                except asyncio.LimitOverrunError:
                    error = InvalidRequestError(f"request is longer than {MAX_LINE_BYTES} bytes")
                    writer.write(encode_error(error))
                    await writer.drain()
                    break
                if not line.strip():
                    continue
                response, stop = await self._dispatch(line)
                writer.write(response)
                await writer.drain()
                if stop:
                    self.request_stop()
                    break
        except OSError:
            pass  # the client went away
        finally:
            self._connections.discard(writer)
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    async def _dispatch(self, line: bytes) -> tuple[bytes, bool]:
        try:
            request = decode_request(line)
            if request.token is None or not hmac.compare_digest(
                request.token.encode(), self._token
            ):
                raise UnauthorizedError("missing or wrong token; it is in the daemon's state file")
            handler = self._handlers.get(request.op)
            if handler is None:
                raise InvalidRequestError(f"unknown operation {request.op!r}")
            await self._ready.wait()
            result = await handler(request.args)
            return encode_ok(result), request.op == "shutdown"
        except DaemonError as exc:
            return encode_error(exc), False
        except Exception:
            logger.exception("error while handling a request")
            return encode_error(InternalError("internal error; see the daemon's log")), False

    # --- operations --------------------------------------------------------------------

    async def _ping(self, args: dict[str, Any]) -> dict[str, Any]:
        _check_keys(args, set())
        return {
            "pid": os.getpid(),
            "port": self._port,
            "version": __version__,
            "running_jobs": self._scheduler.running_count,
            "queued_jobs": self._scheduler.queued_count,
        }

    async def _submit(self, args: dict[str, Any]) -> dict[str, Any]:
        _check_keys(
            args,
            {
                "url",
                "max_pages",
                "max_depth",
                "concurrency",
                "per_host_concurrency",
                "respect_robots",
                "allowed_hosts",
            },
        )
        record = await self._scheduler.submit(
            _str(args, "url"),
            max_pages=_opt_int(args, "max_pages"),
            max_depth=_opt_int(args, "max_depth"),
            concurrency=_opt_int(args, "concurrency"),
            per_host_concurrency=_opt_int(args, "per_host_concurrency"),
            respect_robots=_bool(args, "respect_robots", True),
            allowed_hosts=_str_list(args, "allowed_hosts"),
        )
        return record.to_dict()

    async def _get(self, args: dict[str, Any]) -> dict[str, Any]:
        _check_keys(args, {"id"})
        return (await self._scheduler.get(_str(args, "id"))).to_dict()

    async def _list(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        _check_keys(args, {"status"})
        status = args.get("status")
        if status is not None and status not in set(JobStatus):
            raise InvalidRequestError(
                f"'status' must be one of: {', '.join(str(s) for s in JobStatus)}"
            )
        records = await self._scheduler.list_jobs(None if status is None else JobStatus(status))
        return [record.to_dict() for record in records]

    async def _pages(self, args: dict[str, Any]) -> dict[str, Any]:
        _check_keys(args, {"id", "offset", "limit"})
        offset, limit = _slice(args)
        pages, total = await self._scheduler.pages(_str(args, "id"), offset, limit)
        items = [{"url": page.url, "links": list(page.links)} for page in pages]
        return {"total": total, "offset": offset, "limit": limit, "items": items}

    async def _links(self, args: dict[str, Any]) -> dict[str, Any]:
        _check_keys(args, {"id", "offset", "limit"})
        offset, limit = _slice(args)
        links, total = await self._scheduler.links(_str(args, "id"), offset, limit)
        return {"total": total, "offset": offset, "limit": limit, "items": links}

    async def _cancel(self, args: dict[str, Any]) -> dict[str, Any]:
        _check_keys(args, {"id"})
        return (await self._scheduler.cancel(_str(args, "id"))).to_dict()

    async def _shutdown(self, args: dict[str, Any]) -> dict[str, Any]:
        _check_keys(args, set())
        return {"stopping": True}


# --- lifecycle -------------------------------------------------------------------------


PING_TIMEOUT = 2.0


async def ping_daemon(state: DaemonState) -> bool:
    """Whether the daemon a state file describes is up and answering with that token."""
    try:
        async with asyncio.timeout(PING_TIMEOUT):
            reader, writer = await asyncio.open_connection(HOST, state.port)
            try:
                writer.write(encode_request(Request("ping", state.token)))
                await writer.drain()
                decode_response(await reader.readline())
                return True
            finally:
                writer.close()
    except (OSError, TimeoutError, DaemonError):
        return False


def shared_client(settings: Settings) -> httpx.AsyncClient:
    """The one HTTP client every job fetches through."""
    return httpx.AsyncClient(
        follow_redirects=True,
        # pool=None: under load, wait for a free connection instead of failing.
        timeout=httpx.Timeout(settings.request_timeout, pool=None),
        limits=httpx.Limits(
            max_connections=settings.max_connections,
            max_keepalive_connections=settings.max_connections,
        ),
        headers={"User-Agent": settings.user_agent},
    )


async def run_daemon(
    settings: Settings,
    *,
    fetcher_factory: FetcherFactory | None = None,
    on_ready: Callable[[DaemonState], None] | None = None,
    handle_signals: bool = False,
    flush_interval: float = 0.5,
) -> None:
    """Run the daemon until it is asked to stop.

    Startup: refuse if a daemon is already answering for this data directory,
    listen, open storage, recover jobs, then write the state file. Shutdown:
    stop listening, cancel running jobs (queued ones stay queued), remove the
    state file. Raises :class:`DaemonStartError` (or
    :class:`~crawl_daemon.storage.StorageError`) if it can't start.
    """
    data_dir = settings.resolved_data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    existing = read_state(data_dir)
    if existing is not None and await ping_daemon(existing):
        raise DaemonStartError(
            f"a daemon is already running for {data_dir} (pid {existing.pid}, port {existing.port})"
        )

    client = shared_client(settings)
    factory = fetcher_factory or (lambda: DefaultHttpxFetcher(client=client))
    storage = open_storage(settings.database_url, data_dir)
    scheduler = JobScheduler(settings, storage, factory, flush_interval=flush_interval)
    token = secrets.token_urlsafe(32)
    server = DaemonServer(scheduler, token, port=settings.port)
    try:
        try:
            port = await server.start()
        except OSError as exc:
            raise DaemonStartError(
                f"cannot listen on {HOST}:{settings.port}: {exc.strerror or exc}"
            ) from exc
        if handle_signals and sys.platform != "win32":
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, server.request_stop)

        await storage.open()
        try:
            await scheduler.start()
            state = DaemonState(os.getpid(), port, token, utcnow().isoformat())
            write_state(data_dir, state)
            server.set_ready()
            logger.info("crawld %s listening on %s:%d (pid %d)", __version__, HOST, port, state.pid)
            try:
                if on_ready is not None:
                    on_ready(state)
                await _wait_stopped(server)
            finally:
                logger.info("crawld stopping")
                await server.close()
                await scheduler.shutdown()
                remove_state(data_dir, token)
        finally:
            await storage.aclose()
    finally:
        await server.close()
        await client.aclose()


async def _wait_stopped(server: DaemonServer) -> None:
    if sys.platform != "win32":
        await server.wait_stopped()
        return
    # On Windows, a selector loop blocked in select() only sees Ctrl+C when it wakes up.
    waiter = asyncio.create_task(server.wait_stopped())
    try:
        while not waiter.done():
            await asyncio.wait([waiter], timeout=0.5)
    finally:
        waiter.cancel()
