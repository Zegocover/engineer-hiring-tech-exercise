"""Tests for the CLI adapter layer: argument parsing, wiring, exit codes.

Crawling behaviour (traversal, domain scoping, cycles) is covered by
test_crawler.py and test_integration.py; these tests only exercise what the CLI
itself adds — scheme inference, validation/exit codes, output selection, etc.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from crawler.cli import _ensure_scheme, main


def _html(*hrefs: str) -> httpx.Response:
    body = "".join(f'<a href="{h}">l</a>' for h in hrefs)
    return httpx.Response(
        200,
        headers={"content-type": "text/html"},
        content=f"<html>{body}</html>".encode(),
    )


@respx.mock
def test_text_run_wires_stack_and_splits_stdout_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    respx.get("https://example.com/").mock(return_value=_html("/a"))
    respx.get("https://example.com/a").mock(return_value=_html())

    code = main(["https://example.com/"])
    captured = capsys.readouterr()

    assert code == 0
    assert "https://example.com/" in captured.out
    assert "https://example.com/a" in captured.out
    assert "crawled 2 page(s)" in captured.err  # summary on stderr, not stdout


@respx.mock
def test_json_flag_selects_json_output(capsys: pytest.CaptureFixture[str]) -> None:
    respx.get("https://example.com/").mock(return_value=_html())

    code = main(["--json", "https://example.com/"])
    out = capsys.readouterr().out

    assert code == 0
    record = json.loads(out.splitlines()[0])
    assert record["url"] == "https://example.com/"
    assert "links" in record and "status" in record


@respx.mock
def test_scheme_is_added_when_omitted(capsys: pytest.CaptureFixture[str]) -> None:
    respx.get("https://example.com/").mock(return_value=_html())

    assert main(["example.com"]) == 0
    assert "https://example.com/" in capsys.readouterr().out


@respx.mock
def test_error_pages_are_counted_in_summary(capsys: pytest.CaptureFixture[str]) -> None:
    respx.get("https://example.com/").mock(return_value=_html("/missing"))
    respx.get("https://example.com/missing").mock(
        return_value=httpx.Response(404, headers={"content-type": "text/html"}, content=b"nope")
    )

    assert main(["https://example.com/"]) == 0
    assert "crawled 2 page(s), 1 error(s)" in capsys.readouterr().err


def test_keyboard_interrupt_is_handled_gracefully(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def interrupt(coro: object) -> int:
        coro.close()  # type: ignore[attr-defined]  # avoid "never awaited" warning
        raise KeyboardInterrupt

    monkeypatch.setattr("crawler.cli.asyncio.run", interrupt)

    assert main(["https://example.com/"]) == 130
    assert "interrupted" in capsys.readouterr().err


def test_invalid_url_returns_error_code(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([""]) == 2
    assert "not a valid URL" in capsys.readouterr().err


def test_bad_concurrency_returns_error_code(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--concurrency", "0", "https://example.com/"]) == 2
    assert "concurrency" in capsys.readouterr().err


def test_bad_max_pages_returns_error_code(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--max-pages", "0", "https://example.com/"]) == 2
    assert "max-pages" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("example.com", "https://example.com"),
        ("http://example.com", "http://example.com"),
        ("https://example.com", "https://example.com"),
    ],
)
def test_ensure_scheme(raw: str, expected: str) -> None:
    assert _ensure_scheme(raw) == expected
