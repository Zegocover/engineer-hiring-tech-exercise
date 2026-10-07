from __future__ import annotations

import json

import httpx
import pytest
import respx

from site_crawler.cli import EXIT_OK, EXIT_SEED_FAILED, EXIT_USAGE, main
from site_crawler.models import CrawlConfig

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


@respx.mock
def test_allow_host_follows_links_to_that_host(capsys: pytest.CaptureFixture[str]) -> None:
    respx.get("https://example.com/robots.txt").respond(404)
    respx.get("https://docs.partner.io/robots.txt").respond(404)
    respx.get("https://example.com/").respond(
        200, headers=HTML, text='<a href="https://docs.partner.io/guide">docs</a>'
    )
    respx.get("https://docs.partner.io/guide").respond(200, headers=HTML, text="no links")

    args = [
        "https://example.com/",
        "--allow-host",
        "docs.partner.io",
        "--per-host-concurrency",
        "2",
    ]
    assert main(args) == EXIT_OK
    out, _ = capsys.readouterr()
    assert "https://docs.partner.io/guide\n" in out.splitlines(keepends=True)


def test_allow_host_options_reach_the_config(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[CrawlConfig] = []

    class StopCrawler:
        def __init__(self, config: CrawlConfig, **_: object) -> None:
            seen.append(config)
            raise KeyboardInterrupt

    monkeypatch.setattr("site_crawler.cli.Crawler", StopCrawler)
    main(["https://example.com/", "--allow-host", "*.Example.com", "--allow-host", "docs.io"])

    assert seen[0].allowed_hosts == ("*.example.com", "docs.io")
    assert seen[0].per_host_concurrency is None


def test_invalid_allow_host_exits_with_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["https://example.com/", "--allow-host", "https://other.org/x"]) == EXIT_USAGE
    _, err = capsys.readouterr()
    assert "invalid host pattern 'https://other.org/x'" in err
