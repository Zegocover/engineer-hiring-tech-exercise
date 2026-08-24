"""Data-driven crawl tests: one folder per case under ``cases/``, auto-discovered.

Each case dir holds ``input.txt`` (start path, e.g. ``/``), ``site/`` (HTML served
verbatim), and ``expected.txt`` (host-agnostic page -> links, blocks split by a blank
line: first line is the page, the rest are its links, same-site as ``/path`` and
off-host/mailto absolute). The folder name documents the behaviour under test.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from crawler.cli import main
from crawler.config import Config
from crawler.webcrawler import pool
from crawler.webcrawler.work import Outcome, Page
from tests.support import CASES_DIR, serve_dir

CASE_NAMES = sorted(p.name for p in CASES_DIR.iterdir() if p.is_dir())


def _parse_expected(text: str) -> dict[str, set[str]]:
    pages: dict[str, set[str]] = {}
    for block in text.strip().split("\n\n"):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines:
            page, *links = lines
            pages[page] = set(links)
    return pages


def _crawl(start: str) -> list[Page]:
    pages: list[Page] = []

    def report(outcome: Outcome) -> None:
        if isinstance(outcome, Page):
            pages.append(outcome)

    async def go() -> None:
        async with httpx.AsyncClient() as client:
            await pool.run(start, client, Config(), report)

    asyncio.run(go())
    return pages


@pytest.mark.parametrize("case", CASE_NAMES)
def test_case(case: str) -> None:
    case_dir = CASES_DIR / case
    start_path = (case_dir / "input.txt").read_text().strip()
    expected = _parse_expected((case_dir / "expected.txt").read_text())

    with serve_dir(case_dir / "site") as base:
        root = base.rstrip("/")
        pages = _crawl(root + start_path)

    def rel(url: str) -> str:
        return url[len(root) :] if url.startswith(root) else url

    actual = {rel(p.url): {rel(link) for link in p.links} for p in pages}
    assert actual == expected


def test_downstream_failure_reports_and_continues(capsys: pytest.CaptureFixture[str]) -> None:
    site = CASES_DIR / "downstream-failure" / "site"
    with serve_dir(site) as base:
        code = main([base])

    captured = capsys.readouterr()
    assert code == 0
    assert f"{base}valid.html" in captured.out
    assert f"error: {base}missing.html: status: 404" in captured.err


def test_robots_disallowed_base_fails(capsys: pytest.CaptureFixture[str]) -> None:
    site = CASES_DIR / "robots-excluded" / "site"
    with serve_dir(site) as base:
        code = main([f"{base}private.html"])

    captured = capsys.readouterr()
    assert code == 1
    assert f"error: {base}private.html: disallowed by robots.txt" in captured.err
