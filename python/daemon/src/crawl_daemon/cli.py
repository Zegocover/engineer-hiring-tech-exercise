"""``crawld`` command: run the daemon, and submit, follow, inspect and cancel its jobs.

Results go to standard output; progress, errors and hints to standard error.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import json
import logging
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Any

from site_crawler.models import PageResult
from site_crawler.writers import TextWriter

from crawl_daemon.client import DaemonClient, DaemonNotRunningError
from crawl_daemon.models import (
    ConflictError,
    DaemonError,
    InvalidRequestError,
    JobStatus,
    NotFoundError,
)
from crawl_daemon.server import MAX_SLICE, DaemonStartError, loop_factory, run_daemon
from crawl_daemon.settings import Settings
from crawl_daemon.state import LOG_FILE, pid_alive, read_state
from crawl_daemon.storage import StorageError

EXIT_OK = 0
EXIT_FAILED = 1
"""A waited-on job failed or was cancelled, or the daemon could not start or stop."""
EXIT_USAGE = 2
EXIT_NOT_RUNNING = 3
EXIT_NOT_FOUND = 4
EXIT_CONFLICT = 5
EXIT_INTERRUPTED = 130

POLL_INTERVAL = 0.5
START_TIMEOUT = 10.0
STOP_TIMEOUT = 30.0
BATCH = 500

Command = Callable[[argparse.Namespace, Path], int]


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def _non_negative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must not be negative")
    return number


def _port(value: str) -> int:
    number = int(value)
    if not 0 <= number <= 65535:
        raise argparse.ArgumentTypeError("must be between 0 and 65535")
    return number


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--data-dir",
        metavar="DIR",
        help="the daemon's data directory (default: $CRAWLD_DATA_DIR or a per-user directory)",
    )
    common.add_argument(
        "-v", "--verbose", action="count", default=0, help="more logging (-v info, -vv debug)"
    )
    as_json = argparse.ArgumentParser(add_help=False)
    as_json.add_argument("--json", action="store_true", help="print JSON instead of text")

    daemon = argparse.ArgumentParser(add_help=False)
    daemon.add_argument("--port", type=_port, help="loopback port to listen on (8765; 0: any)")
    daemon.add_argument(
        "--database", metavar="URL", help="sqlite:///PATH or postgresql://... (crawld.db)"
    )
    daemon.add_argument(
        "--max-parallel-jobs", type=_positive_int, metavar="N", help="jobs run at once (2)"
    )
    daemon.add_argument("--no-parse-cache", action="store_true", help="don't reuse parsed links")
    daemon.add_argument(
        "--log-level",
        choices=("debug", "info", "warning", "error"),
        default="info",
        help="daemon log level (info)",
    )

    parser = argparse.ArgumentParser(
        prog="crawld",
        description="Run site crawls in the background and manage them from the command line.",
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    def add(
        name: str, help_text: str, *parents: argparse.ArgumentParser
    ) -> argparse.ArgumentParser:
        return commands.add_parser(name, help=help_text, description=help_text, parents=[*parents])

    add("serve", "run the daemon in the foreground", common, daemon)
    add("start", "start the daemon in the background", common, daemon)
    add("stop", "stop the running daemon", common)
    add("ping", "check whether the daemon is running", common, as_json)

    submit = add("submit", "submit a crawl job", common, as_json)
    submit.add_argument("url", help="absolute http(s) base URL to start from")
    submit.add_argument("--max-pages", type=_positive_int, help="stop after N pages")
    submit.add_argument(
        "--max-depth", type=_non_negative_int, help="follow links at most N hops from the base URL"
    )
    submit.add_argument("-c", "--concurrency", type=_positive_int, help="parallel requests")
    submit.add_argument(
        "--per-host-concurrency", type=_positive_int, metavar="N", help="parallel requests per host"
    )
    submit.add_argument(
        "--allow-host",
        action="append",
        default=[],
        metavar="PATTERN",
        help="also follow links to this host: docs.example.org or *.example.com; repeatable",
    )
    submit.add_argument("--no-robots", action="store_true", help="ignore robots.txt")
    submit.add_argument("--wait", action="store_true", help="wait until the job finishes")

    wait = add("wait", "wait for a job to finish", common, as_json)
    wait.add_argument("id")

    listing = add("list", "list jobs, newest first", common, as_json)
    listing.add_argument("--status", choices=[str(s) for s in JobStatus], help="only this status")

    status = add("status", "show a job's details", common, as_json)
    status.add_argument("id")

    for name, what in (
        ("pages", "a job's pages and their links"),
        ("links", "a job's distinct links"),
    ):
        sub = add(name, f"print {what}", common, as_json)
        sub.add_argument("id")
        sub.add_argument("--offset", type=_non_negative_int, default=0)
        sub.add_argument("--limit", type=_positive_int, default=100, help="at most 1000 (100)")
        sub.add_argument("--all", action="store_true", help="print all of them")

    cancel = add("cancel", "cancel a queued or running job", common, as_json)
    cancel.add_argument("id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "serve":
        logging.basicConfig(
            level=(logging.WARNING, logging.INFO, logging.DEBUG)[min(args.verbose, 2)],
            format="%(levelname)s %(name)s: %(message)s",
            stream=sys.stderr,
        )
    # Avoid UnicodeEncodeError on consoles with narrow encodings (e.g. cp1252).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")

    try:
        settings = _settings(args)
    except ValueError as exc:
        _error(str(exc))
        return EXIT_USAGE
    data_dir = settings.resolved_data_dir
    try:
        return COMMANDS[args.command](args, data_dir)
    except DaemonNotRunningError as exc:
        _error(f"{exc}; start it with `crawld start`")
        return EXIT_NOT_RUNNING
    except InvalidRequestError as exc:
        _error(str(exc))
        return EXIT_USAGE
    except NotFoundError as exc:
        _error(str(exc))
        return EXIT_NOT_FOUND
    except ConflictError as exc:
        _error(str(exc))
        return EXIT_CONFLICT
    except DaemonError as exc:
        _error(str(exc))
        return EXIT_FAILED
    except KeyboardInterrupt:
        _error("interrupted")
        return EXIT_INTERRUPTED


def _settings(args: argparse.Namespace) -> Settings:
    settings = Settings.from_env()
    overrides: dict[str, Any] = {}
    if args.data_dir:
        overrides["data_dir"] = args.data_dir
    if getattr(args, "port", None) is not None:
        overrides["port"] = args.port
    if getattr(args, "database", None):
        overrides["database_url"] = args.database
    if getattr(args, "max_parallel_jobs", None):
        overrides["max_parallel_jobs"] = args.max_parallel_jobs
    if getattr(args, "no_parse_cache", False):
        overrides["parse_cache"] = False
    return dataclasses.replace(settings, **overrides)


def _error(message: str) -> None:
    print(f"crawld: error: {message}", file=sys.stderr)


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False))


# --- the daemon ------------------------------------------------------------------------


def cmd_serve(args: argparse.Namespace, data_dir: Path) -> int:
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    settings = dataclasses.replace(_settings(args), data_dir=str(data_dir))
    handle_signals = threading.current_thread() is threading.main_thread()
    try:
        asyncio.run(run_daemon(settings, handle_signals=handle_signals), loop_factory=loop_factory)
    except (DaemonStartError, StorageError) as exc:
        _error(str(exc))
        return EXIT_FAILED
    except KeyboardInterrupt:
        pass  # the daemon has already stopped cleanly
    return EXIT_OK


def cmd_start(args: argparse.Namespace, data_dir: Path) -> int:
    client = DaemonClient(data_dir)
    running = client.ping()
    if running is not None:
        print(f"crawld is already running (pid {running['pid']}, port {running['port']})")
        return EXIT_OK

    data_dir = data_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "crawl_daemon", "serve", "--data-dir", str(data_dir)]
    command += ["--log-level", args.log_level]
    if args.port is not None:
        command += ["--port", str(args.port)]
    if args.database:
        command += ["--database", args.database]
    if args.max_parallel_jobs:
        command += ["--max-parallel-jobs", str(args.max_parallel_jobs)]
    if args.no_parse_cache:
        command.append("--no-parse-cache")

    log_path = data_dir / LOG_FILE
    with log_path.open("ab") as log:
        log_start = log.tell()
        process = _spawn_detached(command, log)

    client = DaemonClient(data_dir)
    deadline = time.monotonic() + START_TIMEOUT
    while time.monotonic() < deadline:
        info = client.ping()
        if info is not None:
            # The daemon outlives this command, which never waits for it: stop Popen
            # from warning that it is still running.
            process.returncode = 0
            print(f"crawld started (pid {info['pid']}, port {info['port']})")
            return EXIT_OK
        if process.poll() is not None:
            break
        time.sleep(0.1)
    else:
        process.terminate()
        process.wait()

    _error(f"the daemon did not start; its log ({log_path}) says:")
    with log_path.open("rb") as log:
        log.seek(log_start)
        tail = log.read().decode(errors="replace").strip().splitlines()[-20:]
    for line in tail:
        print(f"  {line}", file=sys.stderr)
    return EXIT_FAILED


def _spawn_detached(command: list[str], log: Any) -> subprocess.Popen[bytes]:
    """Start ``command`` in the background, outliving this terminal."""
    if sys.platform == "win32":
        return subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    return subprocess.Popen(
        command, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True
    )


def cmd_stop(args: argparse.Namespace, data_dir: Path) -> int:
    client = DaemonClient(data_dir)
    state = read_state(data_dir)
    if state is None or client.ping() is None:
        print("crawld is not running", file=sys.stderr)
        return EXIT_NOT_RUNNING
    client.call("shutdown")
    deadline = time.monotonic() + STOP_TIMEOUT
    while time.monotonic() < deadline:
        stopped = client.ping() is None and read_state(data_dir) is None
        # A daemon running inside this very process (as in tests) can't be waited out.
        if stopped and (state.pid == os.getpid() or not pid_alive(state.pid)):
            print("crawld stopped")
            return EXIT_OK
        time.sleep(0.1)
    _error(f"the daemon (pid {state.pid}) did not stop within {STOP_TIMEOUT:.0f}s")
    return EXIT_FAILED


def cmd_ping(args: argparse.Namespace, data_dir: Path) -> int:
    info = DaemonClient(data_dir).ping()
    if info is None:
        if args.json:
            _print_json({"running": False})
        else:
            print("crawld is not running", file=sys.stderr)
        return EXIT_NOT_RUNNING
    if args.json:
        _print_json({"running": True, **info})
    else:
        print(
            f"crawld is running (pid {info['pid']}, port {info['port']}): "
            f"{info['running_jobs']} running, {info['queued_jobs']} queued"
        )
    return EXIT_OK


# --- jobs ------------------------------------------------------------------------------


def cmd_submit(args: argparse.Namespace, data_dir: Path) -> int:
    client = DaemonClient(data_dir)
    request: dict[str, Any] = {"url": args.url}
    for name in ("max_pages", "max_depth", "concurrency", "per_host_concurrency"):
        if getattr(args, name) is not None:
            request[name] = getattr(args, name)
    if args.allow_host:
        request["allowed_hosts"] = args.allow_host
    if args.no_robots:
        request["respect_robots"] = False
    record = client.call("submit", **request)
    if not args.wait:
        if args.json:
            _print_json(record)
        else:
            print(record["id"])
        return EXIT_OK
    if not args.json:
        print(record["id"])
    return _wait_for(client, record["id"], as_json=args.json)


def cmd_wait(args: argparse.Namespace, data_dir: Path) -> int:
    return _wait_for(DaemonClient(data_dir), args.id, as_json=args.json)


def _wait_for(client: DaemonClient, job_id: str, *, as_json: bool) -> int:
    last = ""
    try:
        while True:
            record = client.call("get", id=job_id)
            if JobStatus(record["status"]).finished:
                break
            progress = f"{record['status']}: {_stats_text(record['stats'])}"
            if progress != last:
                print(progress, file=sys.stderr)
                last = progress
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print(f"stopped waiting; job {job_id} keeps running", file=sys.stderr)
        return EXIT_INTERRUPTED
    if as_json:
        _print_json(record)
    else:
        print(f"{record['status']}: {_stats_text(record['stats'])}")
        if record["error"]:
            print(f"error: {record['error']}")
    return EXIT_OK if record["status"] == JobStatus.COMPLETED else EXIT_FAILED


def _stats_text(stats: dict[str, int]) -> str:
    return (
        f"{stats['pages']} pages ({stats['fetched']} fetched, {stats['errors']} errors, "
        f"{stats['robots_skipped']} blocked by robots.txt, "
        f"{stats['parse_cache_hits']} from the parse cache)"
    )


def cmd_list(args: argparse.Namespace, data_dir: Path) -> int:
    request = {"status": args.status} if args.status else {}
    records = DaemonClient(data_dir).call("list", **request)
    if args.json:
        _print_json(records)
        return EXIT_OK
    print(f"{'ID':<32}  {'STATUS':<9}  {'PAGES':>6}  {'ERRORS':>6}  {'SUBMITTED':<19}  URL")
    for record in records:
        submitted = record["submitted_at"][:19].replace("T", " ")
        stats = record["stats"]
        print(
            f"{record['id']:<32}  {record['status']:<9}  {stats['pages']:>6}  "
            f"{stats['errors']:>6}  {submitted:<19}  {record['url']}"
        )
    return EXIT_OK


def cmd_status(args: argparse.Namespace, data_dir: Path) -> int:
    record = DaemonClient(data_dir).call("get", id=args.id)
    if args.json:
        _print_json(record)
        return EXIT_OK
    limits = record["limits"]
    rows = [
        ("id", record["id"]),
        ("url", record["url"]),
        ("status", record["status"]),
        ("submitted", record["submitted_at"]),
        ("started", record["started_at"] or "-"),
        ("finished", record["finished_at"] or "-"),
        ("stats", _stats_text(record["stats"])),
        ("max pages", limits["max_pages"]),
        ("max depth", "-" if limits["max_depth"] is None else limits["max_depth"]),
        ("concurrency", limits["concurrency"]),
        ("per host", limits["per_host_concurrency"] or "-"),
        ("robots.txt", "respected" if limits["respect_robots"] else "ignored"),
        ("allowed hosts", ", ".join(limits["allowed_hosts"]) or "-"),
    ]
    if record["error"]:
        rows.append(("error", record["error"]))
    for name, value in rows:
        print(f"{name + ':':<15}{value}")
    return EXIT_OK


def _slices(client: DaemonClient, op: str, args: argparse.Namespace) -> Iterator[dict[str, Any]]:
    """The requested slice, or every slice when ``--all`` is given."""
    if not args.all:
        yield client.call(op, id=args.id, offset=args.offset, limit=min(args.limit, MAX_SLICE))
        return
    offset = args.offset
    while True:
        result: dict[str, Any] = client.call(op, id=args.id, offset=offset, limit=BATCH)
        yield result
        offset += len(result["items"])
        if not result["items"] or offset >= result["total"]:
            return


def cmd_pages(args: argparse.Namespace, data_dir: Path) -> int:
    client = DaemonClient(data_dir)
    for result in _slices(client, "pages", args):
        if args.json and not args.all:
            _print_json(result)
        elif args.json:
            for item in result["items"]:
                _print_json(item)
        else:
            pages = [PageResult(item["url"], tuple(item["links"])) for item in result["items"]]
            _print_pages(pages)
    return EXIT_OK


def _print_pages(pages: list[PageResult]) -> None:
    """Print as the ``crawl`` command does, with the library's text writer."""

    async def write() -> None:
        writer = TextWriter(sys.stdout)
        for page in pages:
            await writer.write(page)
        await writer.aclose()

    asyncio.run(write())


def cmd_links(args: argparse.Namespace, data_dir: Path) -> int:
    client = DaemonClient(data_dir)
    for result in _slices(client, "links", args):
        if args.json and not args.all:
            _print_json(result)
        else:
            for link in result["items"]:
                if args.json:
                    _print_json(link)
                else:
                    print(link)
    return EXIT_OK


def cmd_cancel(args: argparse.Namespace, data_dir: Path) -> int:
    record = DaemonClient(data_dir).call("cancel", id=args.id)
    if args.json:
        _print_json(record)
    else:
        print(f"job {record['id']} is {record['status']}")
    return EXIT_OK


COMMANDS: dict[str, Command] = {
    "serve": cmd_serve,
    "start": cmd_start,
    "stop": cmd_stop,
    "ping": cmd_ping,
    "submit": cmd_submit,
    "wait": cmd_wait,
    "list": cmd_list,
    "status": cmd_status,
    "pages": cmd_pages,
    "links": cmd_links,
    "cancel": cmd_cancel,
}


if __name__ == "__main__":  # pragma: no cover
    with contextlib.suppress(KeyboardInterrupt):
        sys.exit(main())
