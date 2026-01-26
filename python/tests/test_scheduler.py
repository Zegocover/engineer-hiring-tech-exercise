"""Tests for scheduler helpers and queue behaviour."""

import asyncio

import pytest

from crawler import urls
from crawler.models import CrawlItem
from crawler.robots import RobotsPolicy
from crawler.scheduler import Scheduler


@pytest.mark.asyncio
async def test_enqueue_candidate_puts_item() -> None:
    scheduler = Scheduler()
    item = CrawlItem(url="https://example.com", depth=0)

    await scheduler.enqueue_candidate(item)

    queued = await scheduler._candidates.get()
    assert queued == item
    scheduler._candidates.task_done()


@pytest.mark.asyncio
async def test_enqueue_candidate_skips_disallowed_by_robots() -> None:
    scheduler = Scheduler()
    policy = RobotsPolicy(allow=(), disallow=("/blocked",))

    await scheduler.enqueue_candidate(
        CrawlItem(url="https://example.com/blocked/page", depth=0),
        robots_policy=policy,
    )

    assert scheduler._candidates.empty()


@pytest.mark.asyncio
async def test_process_candidate_skips_disallowed_by_robots() -> None:
    scheduler = Scheduler()
    policy = RobotsPolicy(allow=(), disallow=("/blocked",))

    await scheduler.process_candidate(
        CrawlItem(url="https://example.com/blocked/page", depth=0),
        base_url="https://example.com",
        max_depth=2,
        robots_policy=policy,
    )

    assert scheduler._crawl_queue.empty()


@pytest.mark.asyncio
async def test_enqueue_candidate_urls_puts_items() -> None:
    scheduler = Scheduler()
    urls_list = ["https://example.com/a", "https://example.com/b"]

    await scheduler.enqueue_candidate_urls(urls_list, depth=2)

    first = await scheduler._candidates.get()
    second = await scheduler._candidates.get()
    assert first == CrawlItem(url="https://example.com/a", depth=2)
    assert second == CrawlItem(url="https://example.com/b", depth=2)
    scheduler._candidates.task_done()
    scheduler._candidates.task_done()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("candidate_url", "depth", "max_depth", "expected_enqueued"),
    [
        pytest.param(
            "https://example.com/page",
            0,
            2,
            True,
            id="valid-in-scope-enqueued",
        ),
        pytest.param(
            "https://example.com/deep",
            2,
            2,
            False,
            id="beyond-max-depth",
        ),
        pytest.param(
            "mailto:hello@example.com",
            0,
            2,
            False,
            id="unsupported-scheme",
        ),
        pytest.param(
            "/relative/path",
            0,
            2,
            False,
            id="missing-scheme-skips",
        ),
        pytest.param(
            "https://example.org/page",
            0,
            2,
            False,
            id="out-of-scope-domain",
        ),
    ],
)
async def test_process_candidate(
    candidate_url: str,
    depth: int,
    max_depth: int,
    expected_enqueued: bool,
) -> None:
    scheduler = Scheduler()
    base_url = "https://example.com"

    candidate = CrawlItem(url=candidate_url, depth=depth)

    await scheduler.process_candidate(candidate, base_url, max_depth)

    if expected_enqueued:
        queued = await asyncio.wait_for(scheduler.next_crawl_task(), timeout=1)
        assert queued == CrawlItem(url=candidate_url, depth=depth + 1)
        scheduler.crawl_task_done()
    else:
        assert scheduler._crawl_queue.empty()


@pytest.mark.asyncio
async def test_process_candidate_skips_when_already_visited() -> None:
    scheduler = Scheduler()
    base_url = "https://example.com"
    candidate_url = "https://example.com/dup"

    scheduler._visited.add(urls.normalise_for_dedupe(candidate_url))

    await scheduler.process_candidate(
        CrawlItem(url=candidate_url, depth=0), base_url, max_depth=2
    )

    assert scheduler._crawl_queue.empty()


def test_increment_pages_crawled_stops_at_limit() -> None:
    scheduler = Scheduler(max_pages_crawled=1)
    assert not scheduler.stop_event.is_set()
    assert not scheduler._stop_scheduling.is_set()

    scheduler.increment_pages_crawled()

    assert scheduler._stop_scheduling.is_set()


@pytest.mark.asyncio
async def test_next_crawl_task_returns_none_when_stopped() -> None:
    scheduler = Scheduler()
    scheduler.stop()

    item = await asyncio.wait_for(scheduler.next_crawl_task(), timeout=0.1)

    assert item is None


@pytest.mark.asyncio
async def test_wait_for_shutdown_stops_when_idle() -> None:
    scheduler = Scheduler()

    scheduler._started.set()
    await asyncio.wait_for(scheduler.wait_for_shutdown(), timeout=0.5)

    assert scheduler.stop_event.is_set()
