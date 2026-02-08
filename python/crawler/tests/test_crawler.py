from __future__ import annotations

import logging

import pytest

from crawler.crawler import Crawler
from crawler.worker import Result


def test_crawler_accepts_valid_defaults() -> None:
    crawler = Crawler("https://example.com")
    assert crawler._batch_size == 10
    assert crawler._max_urls is None
    assert crawler._timeout == 10.0
    assert crawler._retries == 1


@pytest.mark.asyncio
async def test_crawler_is_single_use(monkeypatch: pytest.MonkeyPatch) -> None:
    crawler = Crawler("https://example.com")

    async def _fetch(self, url: str) -> Result:
        return Result(url=url, links=[], crawlable_links=[])

    monkeypatch.setattr("crawler.worker.Worker.fetch", _fetch)

    await crawler.crawl()
    with pytest.raises(RuntimeError):
        await crawler.crawl()


@pytest.mark.asyncio
async def test_crawler_retries_failed_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, int] = {}
    crawler = Crawler("https://example.com", retries=1)

    async def _fetch(self, url: str) -> Result:
        calls[url] = calls.get(url, 0) + 1
        if calls[url] == 1:
            return Result(url=url, links=[], crawlable_links=[], error="boom")
        return Result(url=url, links=[], crawlable_links=[])

    monkeypatch.setattr("crawler.worker.Worker.fetch", _fetch)

    await crawler.crawl()

    assert calls["https://example.com"] == 2
    assert len(crawler._results) == 1


@pytest.mark.asyncio
async def test_crawler_writes_output_file(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_path = tmp_path / "out.txt"
    crawler = Crawler(
        "https://example.com",
        output=str(output_path),
        quiet=True,
    )

    async def _fetch(self, url: str) -> Result:
        return Result(
            url=url,
            links=["https://example.com/a", "https://example.com/b"],
            crawlable_links=[],
        )

    monkeypatch.setattr("crawler.worker.Worker.fetch", _fetch)

    await crawler.crawl()

    output = output_path.read_text(encoding="utf-8")
    assert output.startswith("[1]: https://example.com")
    assert " - [1]: https://example.com/a" in output
    assert " - [2]: https://example.com/b" in output


@pytest.mark.asyncio
async def test_crawler_logs_progress(caplog, monkeypatch: pytest.MonkeyPatch) -> None:
    caplog.set_level(logging.INFO)
    crawler = Crawler("https://example.com")

    async def _fetch(self, url: str) -> Result:
        return Result(url=url, links=[], crawlable_links=[])

    monkeypatch.setattr("crawler.worker.Worker.fetch", _fetch)

    await crawler.crawl()

    messages = [record.getMessage() for record in caplog.records]
    assert any("Starting crawl" in message for message in messages)
    assert any("Crawl finished" in message for message in messages)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"batch_size": 0},
        {"batch_size": 11},
        {"max_urls": 0},
        {"max_urls": 1001},
        {"timeout": -0.1},
        {"timeout": 10.1},
        {"retries": -1},
        {"retries": 4},
    ],
)
def test_crawler_rejects_invalid_bounds(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        Crawler("https://example.com", **kwargs)
