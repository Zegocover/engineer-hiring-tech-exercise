from __future__ import annotations

import subprocess
import sys

import pytest

from crawler.cli import main, make_reporter
from crawler.webcrawler.outcome import Page
from tests.support import CASES_DIR, serve_dir

SITE = CASES_DIR / "mixed-links" / "site"


def test_usage_when_no_args(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err


@pytest.mark.parametrize("url", ["not-a-url", "http://example.com:bad", "http://[::1"])
def test_rejects_invalid_url(url: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([url]) == 2
    assert "error:" in capsys.readouterr().err


def test_bad_config_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CRAWLER_WORKERS", "-1")  # a valid URL, so we reach Config()
    assert main(["https://example.com"]) == 2
    assert "error:" in capsys.readouterr().err


def test_happy_crawl_prints_blocks(capsys: pytest.CaptureFixture[str]) -> None:
    with serve_dir(SITE) as base:
        code = main([base])
    assert code == 0
    out = capsys.readouterr().out
    assert base in out
    assert f"{base}a.html" in out  # links print as absolute URLs


def test_reporter_dedupes_links_within_a_block(capsys: pytest.CaptureFixture[str]) -> None:
    report = make_reporter()
    report(Page("http://h/", ("http://h/a", "http://h/a", "http://h/b")))
    assert capsys.readouterr().out == "http://h/\nhttp://h/a\nhttp://h/b\n\n"


def test_failed_base_exits_1(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["http://127.0.0.1:1/"])  # nothing listening → connection refused
    assert code == 1
    assert "error:" in capsys.readouterr().err


def test_non_html_base_exits_0(capsys: pytest.CaptureFixture[str]) -> None:
    with serve_dir(SITE) as base:
        code = main([f"{base}data.json"])
    assert code == 0
    assert not capsys.readouterr().err


def test_module_invocation_usage() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "crawler"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 2
    assert "usage" in result.stderr
