"""Integration-style tests for app wiring."""

import pytest

from crawler import app, config
from crawler.fetcher import FetchResult


class DummyFetcher:
    def __init__(self, user_agent: str, timeout_s: int) -> None:
        self._user_agent = user_agent
        self._timeout_s = timeout_s

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def fetch_html(self, url: str) -> FetchResult:
        return FetchResult(
            url=url,
            status=200,
            content_type="text/html",
            body="<html><body>No links</body></html>",
        )


@pytest.mark.asyncio
async def test_run_async_wires_components(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(app, "Fetcher", DummyFetcher)

    profile = config.CrawlProfile(
        name="test",
        max_pages_crawled=1,
        max_depth=1,
        concurrency=1,
        timeout_seconds=5,
        max_attempts=1,
    )
    cfg = config.CrawlerConfig(
        base_url="https://example.com",
        profile=profile,
        output_format=config.OUTPUT_TEXT,
        output_file=str(tmp_path / "out.txt"),
        robots=config.ROBOTS_IGNORE,
        user_agent="test-agent",
        strip_fragments=True,
        only_http_links=True,
        only_in_scope_links=True,
        verbose=False,
    )

    await app.run_async(cfg)

    output = (tmp_path / "out.txt").read_text(encoding="utf-8")
    assert "https://example.com" in output
