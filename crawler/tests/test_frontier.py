import asyncio

import pytest

from crawler.src.frontier import Frontier


def test_add_enqueues_new_url() -> None:
    frontier = Frontier()
    frontier.add("https://example.com/a")
    assert frontier._queue.qsize() == 1


def test_add_dedups_repeated_url() -> None:
    frontier = Frontier()
    frontier.add("https://example.com/a")
    frontier.add("https://example.com/a")
    assert frontier._queue.qsize() == 1


def test_mark_visited_prevents_future_add() -> None:
    frontier = Frontier()
    frontier.mark_visited("https://example.com/a")
    frontier.add("https://example.com/a")
    assert frontier._queue.qsize() == 0


@pytest.mark.asyncio
async def test_next_returns_added_url() -> None:
    frontier = Frontier()
    frontier.add("https://example.com/a")
    url = await frontier.next()
    assert url == "https://example.com/a"


@pytest.mark.asyncio
async def test_join_completes_after_task_done() -> None:
    frontier = Frontier()
    frontier.add("https://example.com/a")

    async def worker() -> None:
        url = await frontier.next()
        assert url == "https://example.com/a"
        frontier.task_done()

    task = asyncio.create_task(worker())
    await asyncio.wait_for(frontier.join(), timeout=1.0)
    await task


@pytest.mark.asyncio
async def test_join_waits_for_in_flight_additions() -> None:
    frontier = Frontier()
    frontier.add("https://example.com/a")
    joined = False

    async def worker() -> None:
        nonlocal joined
        url = await frontier.next()
        frontier.add("https://example.com/b")  # simulate discovering a new link
        frontier.task_done()
        if url == "https://example.com/b":
            joined = True

    task1 = asyncio.create_task(worker())
    task2 = asyncio.create_task(worker())
    await asyncio.wait_for(frontier.join(), timeout=1.0)
    await asyncio.gather(task1, task2)
    assert joined
