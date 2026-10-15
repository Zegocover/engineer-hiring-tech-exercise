import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Any

import pytest
from site_crawler.interfaces import Fetcher
from site_crawler.models import FetchResult, PageResult

from crawl_daemon.components import cache_key
from crawl_daemon.models import (
    ConflictError,
    InvalidRequestError,
    JobLimits,
    JobRecord,
    JobStats,
    JobStatus,
    NotFoundError,
    utcnow,
)
from crawl_daemon.scheduler import INTERRUPTED, JobScheduler
from crawl_daemon.settings import Settings
from crawl_daemon.storage import Storage
from tests.fakes import BASE, FakeSite, GatedSite, chain_site, html

SchedulerFactory = Callable[..., Awaitable[JobScheduler]]


@pytest.fixture
async def make_scheduler(storage: Storage) -> AsyncIterator[SchedulerFactory]:
    """Starts schedulers on the test storage; all are shut down after the test."""
    started: list[JobScheduler] = []

    async def make(
        site: Fetcher, storage_override: Storage | None = None, **settings: Any
    ) -> JobScheduler:
        scheduler = JobScheduler(
            Settings(**settings), storage_override or storage, lambda: site, flush_interval=0.01
        )
        await scheduler.start()
        started.append(scheduler)
        return scheduler

    yield make
    for scheduler in started:
        await scheduler.shutdown()


async def until(check: Callable[[], Awaitable[bool]]) -> None:
    async with asyncio.timeout(5):
        for _ in iter(int, 1):  # forever, until the timeout
            if await check():
                return
            await asyncio.sleep(0.005)


async def finished(scheduler: JobScheduler, job_id: str) -> JobRecord:
    async def done() -> bool:
        return (await scheduler.get(job_id)).status.finished

    await until(done)
    return await scheduler.get(job_id)


async def status_is(scheduler: JobScheduler, job_id: str, status: JobStatus) -> None:
    async def check() -> bool:
        return (await scheduler.get(job_id)).status is status

    await until(check)


async def all_pages(scheduler: JobScheduler, job_id: str) -> list[PageResult]:
    pages, total = await scheduler.pages(job_id, 0, 10_000)
    assert len(pages) == total
    return pages


# --- submitting ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "limits", "message"),
    [
        ("ftp://example.com/", {}, "absolute http"),
        (BASE, {"max_depth": -1}, "max_depth"),
        (BASE, {"max_pages": 10_001}, "max_pages must be at most 10000"),
        (BASE, {"concurrency": 33}, "concurrency must be at most 32"),
        (BASE, {"per_host_concurrency": 33}, "per_host_concurrency must be at most 32"),
        (BASE, {"max_pages": 0}, "max_pages"),
        (BASE, {"allowed_hosts": ["https://x/"]}, "host name only"),
    ],
)
async def test_invalid_jobs_rejected(
    make_scheduler: SchedulerFactory, url: str, limits: dict[str, Any], message: str
) -> None:
    scheduler = await make_scheduler(FakeSite({}))
    with pytest.raises(InvalidRequestError, match=message):
        await scheduler.submit(url, **limits)
    assert await scheduler.list_jobs() == []


async def test_defaults_applied(make_scheduler: SchedulerFactory) -> None:
    scheduler = await make_scheduler(FakeSite({BASE: []}), default_max_pages=7)
    record = await scheduler.submit(BASE, max_depth=2)
    assert record.limits == JobLimits(max_pages=7, concurrency=8, max_depth=2)
    stored = (await scheduler.list_jobs())[0]
    assert stored.limits == record.limits


async def test_job_runs_to_completion(make_scheduler: SchedulerFactory) -> None:
    site = FakeSite({BASE: ["/a", "https://other.org/"], BASE + "a": ["/"]})
    scheduler = await make_scheduler(site)
    record = await scheduler.submit(BASE)
    done = await finished(scheduler, record.id)
    assert done.status is JobStatus.COMPLETED
    assert done.started_at is not None
    assert done.finished_at is not None
    assert done.stats.pages == 2
    assert await all_pages(scheduler, record.id) == [
        PageResult(BASE, (BASE + "a", "https://other.org/")),
        PageResult(BASE + "a", (BASE,)),
    ]
    # Off-host link reported but not fetched.
    assert site.calls["https://other.org/"] == 0
    links, total = await scheduler.links(record.id, 0, 10)
    assert (links, total) == ([BASE + "a", "https://other.org/", BASE], 3)


async def test_default_budget_bounds_pages(make_scheduler: SchedulerFactory) -> None:
    scheduler = await make_scheduler(FakeSite(chain_site(10)), default_max_pages=3)
    record = await scheduler.submit(BASE)
    done = await finished(scheduler, record.id)
    assert done.stats.pages == 3


async def test_newest_first_and_status_filter(make_scheduler: SchedulerFactory) -> None:
    site = GatedSite(
        {"https://a.example/": [], "https://b.example/": []}, gated={"https://b.example/"}
    )
    scheduler = await make_scheduler(site)
    a = await scheduler.submit("https://a.example/")
    b = await scheduler.submit("https://b.example/")
    await finished(scheduler, a.id)
    assert [j.id for j in await scheduler.list_jobs()] == [b.id, a.id]
    assert [j.id for j in await scheduler.list_jobs(JobStatus.RUNNING)] == [b.id]
    site.gate.set()


# --- queueing --------------------------------------------------------------------------


async def test_job_waits_for_a_free_slot(make_scheduler: SchedulerFactory) -> None:
    site = GatedSite(
        {"https://a.example/": [], "https://b.example/": []}, gated={"https://a.example/"}
    )
    scheduler = await make_scheduler(site, max_parallel_jobs=1)
    a = await scheduler.submit("https://a.example/")
    b = await scheduler.submit("https://b.example/")
    await status_is(scheduler, a.id, JobStatus.RUNNING)
    queued = await scheduler.get(b.id)
    assert queued.status is JobStatus.QUEUED
    assert (queued.started_at, queued.stats) == (None, JobStats())
    assert (scheduler.running_count, scheduler.queued_count) == (1, 1)
    site.gate.set()
    assert (await finished(scheduler, b.id)).status is JobStatus.COMPLETED


async def test_first_in_first_out(make_scheduler: SchedulerFactory) -> None:
    urls = ["https://a.example/", "https://b.example/", "https://c.example/"]
    site = GatedSite({url: [] for url in urls}, gated={urls[0]})
    scheduler = await make_scheduler(site, max_parallel_jobs=1)
    a, b, c = [await scheduler.submit(url) for url in urls]
    site.gate.set()
    done_b, done_c = await finished(scheduler, b.id), await finished(scheduler, c.id)
    assert done_b.started_at is not None
    assert done_c.started_at is not None
    assert done_b.started_at < done_c.started_at
    assert (await scheduler.get(a.id)).status is JobStatus.COMPLETED


# --- failures --------------------------------------------------------------------------


async def test_one_failing_page_still_completes(make_scheduler: SchedulerFactory) -> None:
    site = FakeSite({BASE: ["/ok", "/bad"], BASE + "ok": []}, failing={BASE + "bad"})
    scheduler = await make_scheduler(site)
    done = await finished(scheduler, (await scheduler.submit(BASE)).id)
    assert done.status is JobStatus.COMPLETED
    assert (done.stats.pages, done.stats.errors) == (2, 1)


async def test_unreachable_seed_fails(make_scheduler: SchedulerFactory) -> None:
    scheduler = await make_scheduler(FakeSite({}, failing={BASE}))
    done = await finished(scheduler, (await scheduler.submit(BASE)).id)
    assert done.status is JobStatus.FAILED
    assert done.error == f"could not fetch base URL {BASE}"


async def test_unexpected_error_fails_only_that_job(make_scheduler: SchedulerFactory) -> None:
    site = FakeSite({BASE: ["/boom"], "https://ok.example/": []}, broken={BASE + "boom"})
    scheduler = await make_scheduler(site)
    bad = await scheduler.submit(BASE)
    good = await scheduler.submit("https://ok.example/")
    done = await finished(scheduler, bad.id)
    assert done.status is JobStatus.FAILED
    assert done.error is not None
    assert "RuntimeError: bug while fetching" in done.error
    assert (await finished(scheduler, good.id)).status is JobStatus.COMPLETED


class FailWritesFor:
    """A storage whose page writes fail for one job only."""

    def __init__(self, inner: Storage, job_url: str) -> None:
        self.inner = inner
        self.job_url = job_url
        self.failing_ids: set[str] = set()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    async def create_job(self, job: JobRecord) -> None:
        if job.url == self.job_url:
            self.failing_ids.add(job.id)
        await self.inner.create_job(job)

    async def append_results(
        self, job_id: str, pages: Sequence[tuple[int, PageResult]], *args: Any
    ) -> None:
        if job_id in self.failing_ids and pages:
            raise RuntimeError("disk full")
        await self.inner.append_results(job_id, pages, *args)


async def test_storage_failure_fails_only_that_job(
    make_scheduler: SchedulerFactory, storage: Storage
) -> None:
    site = FakeSite({BASE: [], "https://ok.example/": []})
    faulty: Any = FailWritesFor(storage, BASE)
    scheduler = await make_scheduler(site, storage_override=faulty)
    bad = await scheduler.submit(BASE)
    good = await scheduler.submit("https://ok.example/")
    done = await finished(scheduler, bad.id)
    assert done.status is JobStatus.FAILED
    assert done.error is not None
    assert "could not store results: disk full" in done.error
    assert (await finished(scheduler, good.id)).status is JobStatus.COMPLETED
    assert (await storage.get_job(bad.id)) == done


# --- parse cache -----------------------------------------------------------------------


async def test_unchanged_site_hits_the_cache(make_scheduler: SchedulerFactory) -> None:
    site = FakeSite(chain_site(5))
    scheduler = await make_scheduler(site)
    first = await finished(scheduler, (await scheduler.submit(BASE)).id)
    second = await finished(scheduler, (await scheduler.submit(BASE)).id)
    assert (first.stats.parse_cache_hits, second.stats.parse_cache_hits) == (0, 5)
    assert await all_pages(scheduler, first.id) == await all_pages(scheduler, second.id)


async def test_changed_page_is_parsed_again(make_scheduler: SchedulerFactory) -> None:
    site = FakeSite({BASE: ["/old"], BASE + "old": [], BASE + "new": []})
    scheduler = await make_scheduler(site)
    await finished(scheduler, (await scheduler.submit(BASE)).id)
    site.pages[BASE] = ["/new"]
    second = await finished(scheduler, (await scheduler.submit(BASE)).id)
    pages = await all_pages(scheduler, second.id)
    assert pages[0] == PageResult(BASE, (BASE + "new",))
    assert BASE + "old" not in (await scheduler.links(second.id, 0, 10))[0]
    assert second.stats.parse_cache_hits == 0  # the base page changed and /new is new


async def test_disabled_cache(make_scheduler: SchedulerFactory, storage: Storage) -> None:
    site = FakeSite(chain_site(3))
    scheduler = await make_scheduler(site, parse_cache=False)
    for _ in range(2):
        done = await finished(scheduler, (await scheduler.submit(BASE)).id)
        assert done.stats.parse_cache_hits == 0

    key = cache_key(FetchResult(BASE, BASE, 200, "text/html", html([BASE + "1"])))
    assert await storage.get_parsed_links([key]) == {}


# --- cancelling ------------------------------------------------------------------------


async def test_cancel_running_job_keeps_its_pages(make_scheduler: SchedulerFactory) -> None:
    site = GatedSite(chain_site(6), gated={BASE + "3"})
    scheduler = await make_scheduler(site)
    record = await scheduler.submit(BASE, concurrency=1)

    async def three_reported() -> bool:
        return (await scheduler.get(record.id)).stats.pages == 3

    await until(three_reported)
    cancelled = await scheduler.cancel(record.id)
    assert cancelled.status is JobStatus.CANCELLED
    site.gate.set()
    await asyncio.sleep(0.05)
    assert site.calls[BASE + "4"] == 0
    assert len(await all_pages(scheduler, record.id)) == 3
    assert (await scheduler.get(record.id)).status is JobStatus.CANCELLED


async def test_cancel_queued_job_never_starts(make_scheduler: SchedulerFactory) -> None:
    site = GatedSite(
        {"https://a.example/": [], "https://b.example/": []}, gated={"https://a.example/"}
    )
    scheduler = await make_scheduler(site, max_parallel_jobs=1)
    a = await scheduler.submit("https://a.example/")
    b = await scheduler.submit("https://b.example/")
    assert (await scheduler.cancel(b.id)).status is JobStatus.CANCELLED
    site.gate.set()
    await finished(scheduler, a.id)
    await asyncio.sleep(0.05)
    assert site.calls["https://b.example/"] == 0
    stored = await scheduler.get(b.id)
    assert (stored.status, stored.started_at) == (JobStatus.CANCELLED, None)


async def test_cancel_finished_job_conflicts(make_scheduler: SchedulerFactory) -> None:
    scheduler = await make_scheduler(FakeSite({BASE: []}))
    record = await finished(scheduler, (await scheduler.submit(BASE)).id)
    with pytest.raises(ConflictError, match="already completed"):
        await scheduler.cancel(record.id)
    assert (await scheduler.get(record.id)).status is JobStatus.COMPLETED


async def test_unknown_job(make_scheduler: SchedulerFactory) -> None:
    scheduler = await make_scheduler(FakeSite({}))
    for call in (scheduler.get("nope"), scheduler.cancel("nope"), scheduler.pages("nope", 0, 1)):
        with pytest.raises(NotFoundError):
            await call


async def test_cancelling_one_job_leaves_another_running(make_scheduler: SchedulerFactory) -> None:
    site = GatedSite(
        {"https://a.example/": [], "https://b.example/": ["/x"], "https://b.example/x": []},
        gated={"https://a.example/", "https://b.example/x"},
    )
    scheduler = await make_scheduler(site)
    a = await scheduler.submit("https://a.example/")
    b = await scheduler.submit("https://b.example/")
    await status_is(scheduler, b.id, JobStatus.RUNNING)
    await scheduler.cancel(a.id)
    assert (await scheduler.get(b.id)).status is JobStatus.RUNNING
    site.gate.set()
    done = await finished(scheduler, b.id)
    assert (done.status, done.stats.pages) == (JobStatus.COMPLETED, 2)


# --- stopping and restarting -----------------------------------------------------------


async def test_shutdown_then_restart(make_scheduler: SchedulerFactory, storage: Storage) -> None:
    site = GatedSite(chain_site(4), gated={BASE + "2"})
    first = JobScheduler(Settings(max_parallel_jobs=1), storage, lambda: site, flush_interval=0.01)
    await first.start()
    a = await first.submit(BASE, concurrency=1)
    b = await first.submit("https://b.example/")

    async def two_reported() -> bool:
        return (await first.get(a.id)).stats.pages == 2

    await until(two_reported)
    await first.shutdown()

    stored_a, stored_b = await storage.get_job(a.id), await storage.get_job(b.id)
    assert stored_a is not None
    assert stored_b is not None
    assert stored_a.status is JobStatus.CANCELLED
    assert (await storage.read_pages(a.id, 0, 10))[1] == 2
    assert stored_b.status is JobStatus.QUEUED
    with pytest.raises(ConflictError):
        await first.submit(BASE)

    site.pages["https://b.example/"] = []
    second = await make_scheduler(site)
    assert (await finished(second, b.id)).status is JobStatus.COMPLETED


async def test_crash_recovery(make_scheduler: SchedulerFactory, storage: Storage) -> None:
    crashed = JobRecord(
        id="crashed",
        url=BASE,
        limits=JobLimits(max_pages=10, concurrency=1),
        status=JobStatus.RUNNING,
        submitted_at=utcnow(),
        started_at=utcnow(),
    )
    await storage.create_job(crashed)
    pages = [(n, PageResult(f"{BASE}{n}", ())) for n in range(4)]
    await storage.append_results("crashed", pages, [], JobStats(pages=4))

    scheduler = await make_scheduler(FakeSite({}))
    record = await scheduler.get("crashed")
    assert (record.status, record.error) == (JobStatus.FAILED, INTERRUPTED)
    assert len(await all_pages(scheduler, "crashed")) == 4
