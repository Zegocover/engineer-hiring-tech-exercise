import json
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from site_crawler.interfaces import Fetcher

from crawl_daemon import cli
from crawl_daemon.cli import (
    EXIT_CONFLICT,
    EXIT_FAILED,
    EXIT_NOT_FOUND,
    EXIT_NOT_RUNNING,
    EXIT_OK,
    EXIT_USAGE,
    main,
)
from crawl_daemon.client import DaemonClient
from crawl_daemon.state import read_state
from tests.daemon_thread import DaemonThread
from tests.fakes import BASE, FakeSite, GatedSite

SITE = {BASE: ["/a", "/b"], BASE + "a": ["/b", "/c"], BASE + "b": [], BASE + "c": []}

DaemonStarter = Callable[..., DaemonThread]


@pytest.fixture(autouse=True)
def fast_polling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "POLL_INTERVAL", 0.01)


@pytest.fixture
def start_daemon(tmp_path: Path) -> Iterator[DaemonStarter]:
    started: list[DaemonThread] = []

    def start(site: Fetcher | None = None, **settings: Any) -> DaemonThread:
        daemon = DaemonThread(tmp_path, site or FakeSite(SITE), **settings).start()
        started.append(daemon)
        return daemon

    yield start
    for daemon in started:
        daemon.stop()


class Crawld:
    """Runs ``crawld`` against the test data directory and captures its output."""

    def __init__(self, data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self.data_dir = data_dir
        self.capsys = capsys

    def __call__(self, *args: str) -> tuple[int, str, str]:
        self.capsys.readouterr()  # drop anything printed before
        code = main([*args, "--data-dir", str(self.data_dir)])
        out, err = self.capsys.readouterr()
        return code, out, err

    def json(self, *args: str) -> Any:
        code, out, err = self(*args, "--json")
        assert code == EXIT_OK, err
        return json.loads(out)

    def submit_and_wait(self, *args: str) -> str:
        code, out, err = self("submit", BASE, "--wait", *args)
        assert code == EXIT_OK, err
        return out.splitlines()[0]


@pytest.fixture
def crawld(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> Crawld:
    return Crawld(tmp_path, capsys)


# --- no daemon -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [["list"], ["status", "x"], ["submit", BASE], ["cancel", "x"], ["pages", "x"], ["wait", "x"]],
)
def test_no_daemon(crawld: Crawld, command: list[str]) -> None:
    code, out, err = crawld(*command)
    assert code == EXIT_NOT_RUNNING
    assert "not running" in err
    assert "crawld start" in err
    assert out == ""


def test_ping_without_daemon(crawld: Crawld) -> None:
    code, _, err = crawld("ping")
    assert (code, err.strip()) == (EXIT_NOT_RUNNING, "crawld is not running")
    code, out, _ = crawld("ping", "--json")
    assert (code, json.loads(out)) == (EXIT_NOT_RUNNING, {"running": False})


def test_stop_without_daemon(crawld: Crawld) -> None:
    assert crawld("stop")[0] == EXIT_NOT_RUNNING


def test_usage_errors_exit_2(crawld: Crawld) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["submit"])
    assert exc.value.code == EXIT_USAGE
    with pytest.raises(SystemExit):
        main(["list", "--status", "sleeping"])


def test_bad_environment_setting(crawld: Crawld, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRAWLD_MAX_PARALLEL_JOBS", "many")
    code, _, err = crawld("list")
    assert code == EXIT_USAGE
    assert "CRAWLD_MAX_PARALLEL_JOBS" in err


# --- serve and ping --------------------------------------------------------------------


def test_serve_until_shutdown(tmp_path: Path) -> None:
    result: list[int] = []
    thread = threading.Thread(
        target=lambda: result.append(
            main(["serve", "--port", "0", "--data-dir", str(tmp_path), "--log-level", "warning"])
        )
    )
    thread.start()
    client = DaemonClient(tmp_path)
    for _ in range(500):
        info = client.ping()
        if info is not None:
            break
        time.sleep(0.01)
    else:
        pytest.fail("serve did not start")
    state = read_state(tmp_path)
    assert state is not None
    assert info["port"] == state.port
    assert info["pid"] == state.pid
    assert (info["running_jobs"], info["queued_jobs"]) == (0, 0)
    client.call("shutdown")
    thread.join(15)
    assert result == [EXIT_OK]
    assert read_state(tmp_path) is None


def test_ping(start_daemon: DaemonStarter, crawld: Crawld) -> None:
    daemon = start_daemon()
    assert daemon.state is not None
    code, out, _ = crawld("ping")
    assert code == EXIT_OK
    assert f"port {daemon.state.port}" in out
    assert "0 running, 0 queued" in out
    info = crawld.json("ping")
    assert info["running"] is True
    assert info["port"] == daemon.state.port


# --- submitting and waiting ------------------------------------------------------------


def test_submit_prints_id_without_waiting(start_daemon: DaemonStarter, crawld: Crawld) -> None:
    site = GatedSite(SITE, gated={BASE})
    daemon = start_daemon(site)
    code, out, _ = crawld("submit", BASE, "--max-pages", "50")
    job_id = out.strip()
    assert code == EXIT_OK
    assert len(job_id) == 32
    assert crawld.json("status", job_id)["status"] in ("queued", "running")
    daemon.call_soon(site.gate.set)


def test_submit_options_reach_the_job(start_daemon: DaemonStarter, crawld: Crawld) -> None:
    start_daemon()
    record = crawld.json(
        "submit",
        BASE,
        "--max-pages",
        "3",
        "--max-depth",
        "1",
        "-c",
        "2",
        "--per-host-concurrency",
        "1",
        "--allow-host",
        "*.example.com",
        "--allow-host",
        "docs.partner.io",
        "--no-robots",
    )
    assert record["limits"] == {
        "max_pages": 3,
        "max_depth": 1,
        "concurrency": 2,
        "per_host_concurrency": 1,
        "respect_robots": False,
        "allowed_hosts": ["*.example.com", "docs.partner.io"],
    }


def test_rejected_submission(start_daemon: DaemonStarter, crawld: Crawld) -> None:
    start_daemon()
    code, out, err = crawld("submit", "ftp://example.com/")
    assert code == EXIT_USAGE
    assert out == ""
    assert "absolute http(s) URL" in err
    code, _, err = crawld("submit", BASE, "--max-pages", "999999")
    assert (code, "at most" in err) == (EXIT_USAGE, True)


def test_submit_and_wait(start_daemon: DaemonStarter, crawld: Crawld) -> None:
    start_daemon()
    code, out, _ = crawld("submit", BASE, "--wait")
    assert code == EXIT_OK
    job_id, summary = out.splitlines()
    assert len(job_id) == 32
    assert summary.startswith("completed: 4 pages (4 fetched, 0 errors")


def test_wait_json_is_one_document(start_daemon: DaemonStarter, crawld: Crawld) -> None:
    start_daemon()
    record = crawld.json("submit", BASE, "--wait")
    assert (record["status"], record["stats"]["pages"]) == ("completed", 4)


def test_wait_for_failed_job(start_daemon: DaemonStarter, crawld: Crawld) -> None:
    start_daemon(FakeSite({}, failing={BASE}))
    code, out, _ = crawld("submit", BASE, "--wait")
    assert code == EXIT_FAILED
    assert out.splitlines()[1].startswith("failed:")
    assert f"error: could not fetch base URL {BASE}" in out


def test_wait_shows_progress_and_interrupt_leaves_job_running(
    start_daemon: DaemonStarter, crawld: Crawld, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = GatedSite(SITE, gated={BASE + "c"})
    daemon = start_daemon(site)
    job_id = crawld("submit", BASE)[1].strip()

    polls = 0
    real_sleep = time.sleep

    def interrupt_after_a_few(seconds: float) -> None:
        nonlocal polls
        polls += 1
        if polls == 20:
            raise KeyboardInterrupt
        real_sleep(seconds)

    monkeypatch.setattr(time, "sleep", interrupt_after_a_few)
    code, _, err = crawld("wait", job_id)
    monkeypatch.undo()
    assert code == 130
    assert "running: " in err
    assert f"stopped waiting; job {job_id} keeps running" in err
    assert crawld.json("status", job_id)["status"] == "running"
    daemon.call_soon(site.gate.set)
    assert crawld("wait", job_id)[0] == EXIT_OK


# --- inspecting ------------------------------------------------------------------------


def test_list(start_daemon: DaemonStarter, crawld: Crawld) -> None:
    start_daemon()
    first = crawld.submit_and_wait()
    second = crawld.submit_and_wait("--max-pages", "1")
    code, out, _ = crawld("list")
    lines = out.splitlines()
    assert code == EXIT_OK
    assert lines[0].split() == ["ID", "STATUS", "PAGES", "ERRORS", "SUBMITTED", "URL"]
    assert [line.split()[0] for line in lines[1:]] == [second, first]
    assert lines[1].split()[1:3] == ["completed", "1"]
    assert [job["id"] for job in crawld.json("list", "--status", "completed")] == [second, first]
    assert crawld.json("list", "--status", "running") == []


def test_status(start_daemon: DaemonStarter, crawld: Crawld) -> None:
    start_daemon()
    job_id = crawld.submit_and_wait("--max-depth", "1")
    code, out, _ = crawld("status", job_id)
    assert code == EXIT_OK
    fields = dict(line.split(":", 1) for line in out.splitlines())
    assert fields["status"].strip() == "completed"
    assert fields["max depth"].strip() == "1"
    record = crawld.json("status", job_id)
    assert {"id", "status", "limits", "stats"} <= set(record)


def test_pages_text_matches_crawl_command_layout(
    start_daemon: DaemonStarter, crawld: Crawld
) -> None:
    start_daemon()
    job_id = crawld.submit_and_wait()
    code, out, _ = crawld("pages", job_id, "--all")
    assert code == EXIT_OK
    assert out == (
        f"{BASE}\n  {BASE}a\n  {BASE}b\n{BASE}a\n  {BASE}b\n  {BASE}c\n{BASE}b\n{BASE}c\n"
    )


def test_pages_slices_and_json(
    start_daemon: DaemonStarter, crawld: Crawld, monkeypatch: pytest.MonkeyPatch
) -> None:
    start_daemon()
    job_id = crawld.submit_and_wait()
    result = crawld.json("pages", job_id, "--offset", "1", "--limit", "2")
    assert (result["total"], [item["url"] for item in result["items"]]) == (
        4,
        [BASE + "a", BASE + "b"],
    )
    monkeypatch.setattr(cli, "BATCH", 3)  # --all pages through in several requests
    code, out, _ = crawld("pages", job_id, "--all", "--json")
    assert code == EXIT_OK
    assert [json.loads(line)["url"] for line in out.splitlines()] == [
        BASE,
        BASE + "a",
        BASE + "b",
        BASE + "c",
    ]


def test_links(start_daemon: DaemonStarter, crawld: Crawld) -> None:
    start_daemon()
    job_id = crawld.submit_and_wait()
    code, out, _ = crawld("links", job_id, "--all")
    assert (code, out.splitlines()) == (EXIT_OK, [BASE + "a", BASE + "b", BASE + "c"])
    result = crawld.json("links", job_id, "--limit", "1", "--offset", "2")
    assert (result["total"], result["items"]) == (3, [BASE + "c"])
    code, out, _ = crawld("links", job_id, "--all", "--json")
    assert [json.loads(line) for line in out.splitlines()] == [BASE + "a", BASE + "b", BASE + "c"]


def test_unknown_job(start_daemon: DaemonStarter, crawld: Crawld) -> None:
    start_daemon()
    for command in ("status", "pages", "links", "cancel", "wait"):
        code, _, err = crawld(command, "nope")
        assert code == EXIT_NOT_FOUND, command
        assert "no job with id nope" in err


# --- cancelling ------------------------------------------------------------------------


def test_cancel(start_daemon: DaemonStarter, crawld: Crawld) -> None:
    site = GatedSite(SITE, gated={BASE + "c"})
    daemon = start_daemon(site)
    job_id = crawld("submit", BASE)[1].strip()
    code, out, _ = crawld("cancel", job_id)
    assert (code, out.strip()) == (EXIT_OK, f"job {job_id} is cancelled")
    code, _, err = crawld("cancel", job_id)
    assert code == EXIT_CONFLICT
    assert "already cancelled" in err
    daemon.call_soon(site.gate.set)


def test_cancel_finished_job(start_daemon: DaemonStarter, crawld: Crawld) -> None:
    start_daemon()
    job_id = crawld.submit_and_wait()
    code, _, err = crawld("cancel", job_id)
    assert code == EXIT_CONFLICT
    assert "already completed" in err
    assert crawld.json("status", job_id)["status"] == "completed"


def test_stop_in_process_daemon(start_daemon: DaemonStarter, crawld: Crawld) -> None:
    start_daemon()
    code, out, _ = crawld("stop")
    assert (code, out.strip()) == (EXIT_OK, "crawld stopped")
    assert crawld("ping")[0] == EXIT_NOT_RUNNING
