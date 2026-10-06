from __future__ import annotations

import json

import httpx
import pytest
import respx

from site_crawler.cli import EXIT_OK, EXIT_SEED_FAILED, EXIT_USAGE, main

HTML = {"content-type": "text/html"}


def mock_site() -> None:
    respx.get("https://example.com/robots.txt").respond(404)
    respx.get("https://example.com/").respond(200, headers=HTML, text='<a href="/a">a</a>')
    respx.get("https://example.com/a").respond(200, headers=HTML, text="no links")


@respx.mock
def test_text_output_and_summary(capsys: pytest.CaptureFixture[str]) -> None:
    mock_site()
    assert main(["https://example.com/"]) == EXIT_OK
    out, err = capsys.readouterr()
    assert out == "https://example.com/\n  https://example.com/a\nhttps://example.com/a\n"
    assert "Crawled 2 pages" in err


@respx.mock
def test_jsonl_output(capsys: pytest.CaptureFixture[str]) -> None:
    mock_site()
    assert main(["https://example.com/", "--format", "jsonl"]) == EXIT_OK
    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert {r["url"] for r in records} == {"https://example.com/", "https://example.com/a"}
    assert all(set(r) == {"url", "links"} for r in records)


@respx.mock
def test_max_pages_option(capsys: pytest.CaptureFixture[str]) -> None:
    mock_site()
    assert main(["https://example.com/", "--max-pages", "1"]) == EXIT_OK
    assert capsys.readouterr().out == "https://example.com/\n  https://example.com/a\n"


@pytest.mark.parametrize("url", ["example.com", "ftp://example.com/"])
def test_invalid_url_exits_with_usage_error(url: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([url]) == EXIT_USAGE
    assert "absolute http(s) URL" in capsys.readouterr().err


def test_invalid_option_exits_with_usage_error() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["https://example.com/", "--concurrency", "0"])
    assert exc.value.code == EXIT_USAGE


@respx.mock
def test_unreachable_base_url_exits_non_zero(capsys: pytest.CaptureFixture[str]) -> None:
    respx.get("https://example.com/robots.txt").respond(404)
    respx.get("https://example.com/").mock(side_effect=httpx.ConnectError("refused"))
    assert main(["https://example.com/", "--timeout", "1"]) == EXIT_SEED_FAILED
    assert "could not fetch base URL" in capsys.readouterr().err
