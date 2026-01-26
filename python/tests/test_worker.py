"""Tests for worker loop behaviour."""

import asyncio
from types import SimpleNamespace

import pytest

from crawler import config
from crawler.fetcher import (
    FetchResult,
    RedirectFetchError,
    RetryableFetchError,
    UnsupportedContentTypeError,
)
from crawler.models import CrawlItem
from crawler.renderers import TextRenderer
from crawler.scheduler import Scheduler
from crawler.worker import _compute_retry_delay, process_next


class DummyFetcher:
    def __init__(
        self, result: FetchResult | None = None, exc: Exception | None = None
    ):
        self._result = result
        self._exc = exc

    async def fetch_html(self, url: str) -> FetchResult:
        if self._exc:
            raise self._exc
        assert self._result is not None
        return self._result


class RedirectFetcher:
    def __init__(self, location: str | None):
        self._location = location

    async def fetch_html(self, url: str) -> FetchResult:
        raise RedirectFetchError(url, self._location)


class UnsupportedFetcher:
    async def fetch_html(self, url: str) -> FetchResult:
        raise UnsupportedContentTypeError("unsupported")


@pytest.mark.parametrize(
    ("retry_after", "attempts", "expected"),
    [
        pytest.param("5", 0, 5.0, id="retry-after"),
        pytest.param(None, 0, 1.0, id="first-attempt"),
        pytest.param(None, 1, 2.0, id="second-attempt"),
        pytest.param(None, 2, 4.0, id="third-attempt"),
        pytest.param("bad", 2, 4.0, id="invalid-retry-after"),
    ],
)
def test_compute_retry_delay(retry_after, attempts, expected) -> None:
    assert _compute_retry_delay(retry_after, attempts) == expected


@pytest.mark.asyncio
async def test_worker_handles_retryable_error(tmp_path) -> None:
    scheduler = Scheduler()
    renderer = TextRenderer(tmp_path / "out.txt")

    exc = RetryableFetchError("retry", retry_after="0")
    fetcher = DummyFetcher(exc=exc)

    await scheduler.enqueue_crawl_task(
        CrawlItem(url="https://example.com", depth=0)
    )

    await process_next(
        name="worker",
        scheduler=scheduler,
        fetcher=fetcher,  # type: ignore[arg-type]
        renderer=renderer,
        cfg=config.config_from_args(
            SimpleNamespace(
                base_url="https://example.com",
                profile=config.PROFILE_BALANCED,
                output=config.OUTPUT_TEXT,
                output_file=str(tmp_path / "out.txt"),
                robots=config.ROBOTS_IGNORE,
                user_agent="test",
                strip_fragments=True,
                only_http_links=True,
                only_in_scope_links=True,
                verbose=False,
            )
        ),
    )

    retried = await asyncio.wait_for(scheduler.next_crawl_task(), timeout=0.1)
    assert retried.url == "https://example.com"
    assert retried.attempts == 1
    scheduler.crawl_task_done()

    renderer.close()


@pytest.mark.asyncio
async def test_process_next_returns_false_when_stopped(tmp_path) -> None:
    scheduler = Scheduler()
    renderer = TextRenderer(tmp_path / "out.txt")
    scheduler.stop()

    result = await process_next(
        name="worker",
        scheduler=scheduler,
        fetcher=DummyFetcher(exc=RetryableFetchError("retry")),  # type: ignore[arg-type]
        renderer=renderer,
        cfg=config.config_from_args(
            SimpleNamespace(
                base_url="https://example.com",
                profile=config.PROFILE_BALANCED,
                output=config.OUTPUT_TEXT,
                output_file=str(tmp_path / "out.txt"),
                robots=config.ROBOTS_IGNORE,
                user_agent="test",
                strip_fragments=True,
                only_http_links=True,
                only_in_scope_links=True,
                verbose=False,
            )
        ),
    )

    assert result is False
    renderer.close()


@pytest.mark.asyncio
async def test_process_next_dedupes_links(tmp_path) -> None:
    scheduler = Scheduler()
    renderer = TextRenderer(tmp_path / "out.txt")
    await scheduler.enqueue_crawl_task(
        CrawlItem(url="https://example.com", depth=0)
    )

    result = FetchResult(
        url="https://example.com",
        status=200,
        content_type="text/html",
        body=(
            "<a href='https://example.com/a'>A</a>"
            "<a href='https://example.com/a'>A</a>"
            "<a href='https://example.com/b'>B</a>"
        ),
    )
    fetcher = DummyFetcher(result=result)

    await process_next(
        name="worker",
        scheduler=scheduler,
        fetcher=fetcher,  # type: ignore[arg-type]
        renderer=renderer,
        cfg=config.config_from_args(
            SimpleNamespace(
                base_url="https://example.com",
                profile=config.PROFILE_BALANCED,
                output=config.OUTPUT_TEXT,
                output_file=str(tmp_path / "out.txt"),
                robots=config.ROBOTS_IGNORE,
                user_agent="test",
                strip_fragments=True,
                only_http_links=True,
                only_in_scope_links=True,
                verbose=False,
            )
        ),
    )

    text = (tmp_path / "out.txt").read_text(encoding="utf-8")
    assert text.count("https://example.com/a") == 1
    assert text.count("https://example.com/b") == 1


@pytest.mark.asyncio
async def test_process_next_redirect_enqueues_candidate(tmp_path) -> None:
    scheduler = Scheduler()
    renderer = TextRenderer(tmp_path / "out.txt")
    await scheduler.enqueue_crawl_task(
        CrawlItem(url="https://example.com", depth=0)
    )

    fetcher = RedirectFetcher("https://example.com/next")

    await process_next(
        name="worker",
        scheduler=scheduler,
        fetcher=fetcher,  # type: ignore[arg-type]
        renderer=renderer,
        cfg=config.config_from_args(
            SimpleNamespace(
                base_url="https://example.com",
                profile=config.PROFILE_BALANCED,
                output=config.OUTPUT_TEXT,
                output_file=str(tmp_path / "out.txt"),
                robots=config.ROBOTS_IGNORE,
                user_agent="test",
                strip_fragments=True,
                only_http_links=True,
                only_in_scope_links=True,
                verbose=False,
            )
        ),
    )

    candidate = await asyncio.wait_for(
        scheduler._candidates.get(), timeout=0.1
    )
    assert candidate.url == "https://example.com/next"
    scheduler._candidates.task_done()
    renderer.close()


@pytest.mark.asyncio
async def test_process_next_skips_unsupported_content(tmp_path) -> None:
    scheduler = Scheduler()
    renderer = TextRenderer(tmp_path / "out.txt")
    await scheduler.enqueue_crawl_task(
        CrawlItem(url="https://example.com", depth=0)
    )

    fetcher = UnsupportedFetcher()

    await process_next(
        name="worker",
        scheduler=scheduler,
        fetcher=fetcher,  # type: ignore[arg-type]
        renderer=renderer,
        cfg=config.config_from_args(
            SimpleNamespace(
                base_url="https://example.com",
                profile=config.PROFILE_BALANCED,
                output=config.OUTPUT_TEXT,
                output_file=str(tmp_path / "out.txt"),
                robots=config.ROBOTS_IGNORE,
                user_agent="test",
                strip_fragments=True,
                only_http_links=True,
                only_in_scope_links=True,
                verbose=False,
            )
        ),
    )

    assert scheduler._candidates.empty()
    renderer.close()
