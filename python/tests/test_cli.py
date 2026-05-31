from collections.abc import AsyncIterator

import pytest
from typer.testing import CliRunner

import crawler.cli as cli_module
from crawler.cli import app
from domains.crawler.models import PageResult

runner = CliRunner()


class FakeCrawler:
    """Stands in for a real Crawler: yields preset PageResults."""

    def __init__(self, pages: list[PageResult], truncated: bool = False) -> None:
        self._pages = pages
        self.truncated = truncated

    async def crawl(self) -> AsyncIterator[PageResult]:
        for page in self._pages:
            yield page


def _patch_build(monkeypatch: pytest.MonkeyPatch, crawler: FakeCrawler) -> None:
    monkeypatch.setattr(cli_module, "build_crawler", lambda config, client: crawler)


def test_help_lists_crawl_command() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "crawl" in result.stdout


def test_crawl_prints_pages_as_text(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = [
        PageResult(url="http://a.com/", links=("http://a.com/x",), status=200, error=None),
    ]
    _patch_build(monkeypatch, FakeCrawler(pages))
    result = runner.invoke(app, ["crawl", "http://a.com/"])
    assert result.exit_code == 0
    assert "http://a.com/" in result.stdout
    assert "  http://a.com/x" in result.stdout


def test_crawl_json_outputs_jsonl(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = [
        PageResult(url="http://a.com/", links=(), status=200, error=None),
    ]
    _patch_build(monkeypatch, FakeCrawler(pages))
    result = runner.invoke(app, ["crawl", "http://a.com/", "--json"])
    assert result.exit_code == 0
    assert '"url":"http://a.com/"' in result.stdout.replace(" ", "")


def test_crawl_rejects_url_without_host() -> None:
    result = runner.invoke(app, ["crawl", "not-a-url"])
    assert result.exit_code == 2
    assert "host" in result.output.lower()


def test_crawl_rejects_non_http_scheme() -> None:
    result = runner.invoke(app, ["crawl", "ftp://example.com/"])
    assert result.exit_code == 2
    assert "http" in result.output.lower()


def test_crawl_prints_truncation_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = [PageResult(url="http://a.com/", links=(), status=200, error=None)]
    _patch_build(monkeypatch, FakeCrawler(pages, truncated=True))
    result = runner.invoke(app, ["crawl", "http://a.com/", "--max-pages", "1"])
    assert result.exit_code == 0
    assert "max-pages" in result.output
