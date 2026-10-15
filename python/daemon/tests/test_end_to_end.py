"""The real ``crawld`` command and a real background daemon against a local HTTP site."""

import asyncio
import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from site_crawler import cli as crawl_cli

from crawl_daemon.cli import EXIT_OK, main
from crawl_daemon.server import loop_factory
from tests.conftest import POSTGRES_URL, needs_postgres, reset_postgres

PAGES = {
    "/": ["/a.html", "/sub/b.html", "https://other.org/"],
    "/a.html": ["/", "/sub/b.html"],
    "/sub/b.html": ["/a.html", "/c.html", "/slow.html"],
    "/c.html": [],
    "/slow.html": [],
}


class Site:
    """A small site on 127.0.0.1. ``/slow.html`` blocks until :attr:`gate` is set."""

    def __init__(self) -> None:
        self.gate = threading.Event()
        gate = self.gate

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/slow.html":
                    gate.wait(30)
                if self.path not in PAGES:
                    self.send_error(404)
                    return
                body = "".join(f'<a href="{href}">x</a>' for href in PAGES[self.path]).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/"
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self.gate.set()
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def site() -> Iterator[Site]:
    site = Site()
    yield site
    site.close()


class Crawld:
    def __init__(self, data_dir: Path, capsys: pytest.CaptureFixture[str], *daemon_args: str):
        self.data_dir = data_dir
        self.capsys = capsys
        self.daemon_args = daemon_args

    def __call__(self, *args: str) -> str:
        self.capsys.readouterr()
        code = main([*args, "--data-dir", str(self.data_dir)])
        out, err = self.capsys.readouterr()
        assert code == EXIT_OK, f"crawld {' '.join(args)} exited {code}: {err}"
        return out

    def start(self) -> None:
        self("start", "--port", "0", *self.daemon_args)

    def status(self, job_id: str) -> dict[str, object]:
        record: dict[str, object] = json.loads(self("status", job_id, "--json"))
        return record


def crawl_command_output(url: str, capsys: pytest.CaptureFixture[str]) -> str:
    capsys.readouterr()
    assert crawl_cli.main([url, "--max-pages", "4", "-c", "1"]) == 0
    return capsys.readouterr().out


@pytest.mark.parametrize("database", ["sqlite", pytest.param("postgres", marks=needs_postgres)])
def test_end_to_end(
    database: str, site: Site, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    daemon_args = ["--max-parallel-jobs", "1"]
    if database == "postgres":
        asyncio.run(reset_postgres(), loop_factory=loop_factory)
        daemon_args += ["--database", POSTGRES_URL]
    crawld = Crawld(tmp_path, capsys, *daemon_args)
    site.gate.set()  # /slow.html answers at once for now

    crawld.start()
    try:
        # A crawl's pages print exactly as the crawl command prints them.
        out = crawld("submit", site.url, "--max-pages", "4", "-c", "1", "--wait")
        first = out.splitlines()[0]
        assert out.splitlines()[1].startswith("completed: 4 pages")
        assert crawld("pages", first, "--all") == crawl_command_output(site.url, capsys)

        # The same unchanged site again: identical results, all from the parse cache.
        second = crawld("submit", site.url, "--max-pages", "4", "-c", "1", "--wait").split()[0]
        assert crawld("pages", second, "--all") == crawld("pages", first, "--all")
        assert crawld("links", second, "--all") == crawld("links", first, "--all")
        stats = crawld.status(second)["stats"]
        assert isinstance(stats, dict)
        assert stats["parse_cache_hits"] == stats["pages"] == 4

        # Stop with one job running (held on /slow.html) and one queued behind it.
        site.gate.clear()
        running = crawld("submit", site.url, "-c", "1").strip()
        queued = crawld("submit", site.url + "c.html").strip()
        assert crawld.status(queued)["status"] == "queued"
    finally:
        crawld("stop")

    # After a restart, the queued job runs; the one that was running stays cancelled.
    site.gate.set()
    crawld.start()
    try:
        assert crawld.status(running)["status"] == "cancelled"
        assert crawld("wait", queued).startswith("completed: 1 pages")
        assert len(json.loads(crawld("list", "--json"))) == 4
    finally:
        crawld("stop")
