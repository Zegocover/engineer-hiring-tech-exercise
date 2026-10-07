import asyncio
import logging
from collections.abc import Callable
from typing import Any

import pytest
from site_crawler.models import ConfigError

from crawler_api.jobs import CrawlJob, JobStatus
from crawler_api.service import (
    CrawlService,
    JobNotFoundError,
    JobNotRunningError,
    LimitError,
)
from crawler_api.settings import Settings
from tests.fakes import FakeSite, GatedSite

BASE = "https://example.com/"


def make_service(site: FakeSite, settings: Settings | None = None) -> CrawlService:
    return CrawlService(settings or Settings(), lambda: site)


async def finished(job: CrawlJob) -> CrawlJob:
    assert job.task is not None
    await asyncio.wait_for(asyncio.shield(job.task), timeout=5)
    return job


def three_page_site(*, failing: set[str] | None = None, broken: set[str] | None = None) -> FakeSite:
    pages = {BASE: ["/a", "/b"], f"{BASE}a": [], f"{BASE}b": []}
    return FakeSite(pages, failing=failing, broken=broken)


async def test_completed_crawl_reports_stats() -> None:
    service = make_service(three_page_site(failing={f"{BASE}b"}))
    job = await finished(service.start(BASE))
    assert job.status is JobStatus.COMPLETED
    assert job.finished_at is not None
    assert job.stats.pages == 2
    assert job.stats.errors == 1
    assert [page.url for page in job.pages] == [BASE, f"{BASE}a"]
    assert job.error is None


async def test_defaults_applied() -> None:
    settings = Settings(default_max_pages=7, default_concurrency=3)
    job = make_service(three_page_site(), settings).start(BASE)
    assert job.config.max_pages == 7
    assert job.config.concurrency == 3
    await finished(job)


async def test_cross_domain_options_reach_the_crawl() -> None:
    pages = {BASE: ["https://docs.partner.io/guide"], "https://docs.partner.io/guide": []}
    site = FakeSite(pages)
    service = make_service(site)
    job = await finished(
        service.start(BASE, allowed_hosts=["Docs.Partner.io"], per_host_concurrency=2)
    )
    assert job.config.allowed_hosts == ("docs.partner.io",)
    assert job.config.per_host_concurrency == 2
    assert "https://docs.partner.io/guide" in site.calls


async def test_seed_failure_fails_crawl() -> None:
    service = make_service(three_page_site(failing={BASE}))
    job = await finished(service.start(BASE))
    assert job.status is JobStatus.FAILED
    assert job.error == f"could not fetch base URL {BASE}"


async def test_unexpected_component_error_fails_crawl(caplog: pytest.LogCaptureFixture) -> None:
    service = make_service(three_page_site(broken={f"{BASE}a"}))
    with caplog.at_level(logging.ERROR):
        job = await finished(service.start(BASE))
    assert job.status is JobStatus.FAILED
    assert job.error is not None
    assert job.error.startswith("RuntimeError: bug while fetching")
    assert f"crawl {job.id} failed" in caplog.text


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_pages": 11}, "max_pages must be at most 10"),
        ({"concurrency": 5}, "concurrency must be at most 4"),
    ],
)
async def test_limits_rejected_before_anything_is_stored(
    kwargs: dict[str, Any], message: str
) -> None:
    service = make_service(three_page_site(), Settings(max_pages_limit=10, max_concurrency=4))
    with pytest.raises(LimitError, match=message):
        service.start(BASE, **kwargs)
    assert service.list() == []


async def test_invalid_url_rejected_before_anything_is_stored() -> None:
    service = make_service(three_page_site())
    with pytest.raises(ConfigError):
        service.start("ftp://example.com/")
    assert service.list() == []


async def until(condition: Callable[[], bool]) -> None:
    async with asyncio.timeout(5):
        # Polls crawler stats, which have no event to wait on.
        while not condition():  # noqa: ASYNC110
            await asyncio.sleep(0)


def gated_site() -> GatedSite:
    """Home links to four pages; the fourth blocks until the gate opens."""
    pages = {BASE: ["/1", "/2", "/3", "/4"], **{f"{BASE}{n}": [] for n in "1234"}}
    return GatedSite(pages, gated={f"{BASE}4"})


async def test_get_and_list() -> None:
    service = make_service(three_page_site())
    first = service.start(BASE)
    second = service.start("https://example.com/a")
    assert service.get(first.id) is first
    assert service.list() == [second, first]
    with pytest.raises(JobNotFoundError):
        service.get("nope")
    await finished(first)
    await finished(second)


async def test_cancel_running_crawl_keeps_pages() -> None:
    site = gated_site()
    service = make_service(site)
    job = service.start(BASE)
    await until(lambda: job.stats.pages == 4)  # home + /1 /2 /3; /4 is held

    cancelled = await service.cancel(job.id)

    assert cancelled is job
    assert job.status is JobStatus.CANCELLED
    assert job.finished_at is not None
    assert [page.url for page in job.pages] == [BASE, f"{BASE}1", f"{BASE}2", f"{BASE}3"]
    site.gate.set()
    await asyncio.sleep(0)
    assert job.stats.pages == 4  # nothing further was reported


async def test_cancel_finished_crawl_is_rejected() -> None:
    service = make_service(three_page_site())
    job = await finished(service.start(BASE))
    with pytest.raises(JobNotRunningError):
        await service.cancel(job.id)
    assert job.status is JobStatus.COMPLETED


async def test_cancel_unknown_crawl() -> None:
    with pytest.raises(JobNotFoundError):
        await make_service(three_page_site()).cancel("nope")


async def test_cancelling_one_crawl_leaves_another_running() -> None:
    held = gated_site()
    other = three_page_site()
    sites = iter([held, other])
    service = CrawlService(Settings(), lambda: next(sites))
    first = service.start(BASE)
    second = service.start(BASE)
    await until(lambda: first.stats.pages == 4)

    await service.cancel(first.id)
    await finished(second)

    assert first.status is JobStatus.CANCELLED
    assert second.status is JobStatus.COMPLETED
    assert second.stats.pages == 3


async def test_shutdown_cancels_running_crawls() -> None:
    service = make_service(gated_site())
    job = service.start(BASE)
    done = await finished(service.start("https://example.com/1"))
    await until(lambda: job.stats.pages == 4)

    await service.shutdown()

    assert job.status is JobStatus.CANCELLED
    assert done.status is JobStatus.COMPLETED


async def test_cancel_before_crawl_starts() -> None:
    service = make_service(three_page_site())
    job = service.start(BASE)  # task created but not yet scheduled
    await service.cancel(job.id)
    assert job.status is JobStatus.CANCELLED
    assert job.finished_at is not None
