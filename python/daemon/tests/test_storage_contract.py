"""The behaviour every storage must have; runs once per database (see ``db_url``)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from site_crawler.models import PageResult

from crawl_daemon.models import JobLimits, JobRecord, JobStats, JobStatus
from crawl_daemon.storage import Storage, StorageError, open_storage
from crawl_daemon.storage.sql import SqlStorage
from tests.conftest import POSTGRES_URL, StorageOpener, needs_postgres, reset_postgres

T0 = datetime(2026, 10, 1, 12, 0, 0, 123456, tzinfo=UTC)


def job(
    job_id: str = "j1", *, at: datetime = T0, status: JobStatus = JobStatus.QUEUED
) -> JobRecord:
    return JobRecord(
        id=job_id,
        url=f"https://{job_id}.example/",
        limits=JobLimits(max_pages=100, concurrency=4, allowed_hosts=("*.example",)),
        status=status,
        submitted_at=at,
    )


def page(url: str, *links: str) -> PageResult:
    return PageResult(url, links)


async def test_create_and_get_job(storage: Storage) -> None:
    record = job()
    await storage.create_job(record)
    assert await storage.get_job("j1") == record
    assert await storage.get_job("missing") is None


async def test_update_job(storage: Storage) -> None:
    record = job()
    await storage.create_job(record)
    record.status = JobStatus.FAILED
    record.started_at = T0 + timedelta(seconds=1)
    record.finished_at = T0 + timedelta(seconds=2)
    record.error = "could not fetch base URL"
    record.stats = JobStats(pages=10, fetched=11, errors=1, robots_skipped=2, parse_cache_hits=3)
    await storage.update_job(record)
    assert await storage.get_job("j1") == record


async def test_list_newest_first_and_filter(storage: Storage) -> None:
    await storage.create_job(job("a", at=T0))
    await storage.create_job(job("b", at=T0 + timedelta(microseconds=1), status=JobStatus.RUNNING))
    await storage.create_job(job("c", at=T0 + timedelta(seconds=1)))
    assert [j.id for j in await storage.list_jobs()] == ["c", "b", "a"]
    assert [j.id for j in await storage.list_jobs(JobStatus.QUEUED)] == ["c", "a"]
    assert [j.id for j in await storage.list_jobs(JobStatus.RUNNING)] == ["b"]
    assert await storage.list_jobs(JobStatus.CANCELLED) == []


async def test_pages_in_report_order_with_slices(storage: Storage) -> None:
    await storage.create_job(job())
    pages = [page(f"https://j1.example/{i}", f"https://j1.example/{i + 1}") for i in range(5)]
    await storage.append_results("j1", list(enumerate(pages[:3])), [], JobStats(pages=3))
    await storage.append_results("j1", list(enumerate(pages[3:], start=3)), [], JobStats(pages=5))
    assert await storage.read_pages("j1", 0, 100) == (pages, 5)
    assert await storage.read_pages("j1", 2, 2) == (pages[2:4], 5)
    assert await storage.read_pages("j1", 10, 2) == ([], 5)


async def test_page_links_keep_document_order(storage: Storage) -> None:
    await storage.create_job(job())
    links = ("https://j1.example/z", "https://j1.example/a", "https://other.org/")
    await storage.append_results("j1", [(0, page("https://j1.example/", *links))], [], JobStats())
    (stored,), _ = await storage.read_pages("j1", 0, 10)
    assert stored.links == links


async def test_append_updates_live_stats(storage: Storage) -> None:
    await storage.create_job(job())
    await storage.append_results("j1", [], [], JobStats(pages=4, fetched=5, parse_cache_hits=1))
    stored = await storage.get_job("j1")
    assert stored is not None
    assert stored.stats == JobStats(pages=4, fetched=5, parse_cache_hits=1)


async def test_repeated_link_stored_once(storage: Storage) -> None:
    await storage.create_job(job())
    about = "https://j1.example/about"
    await storage.append_results("j1", [], [(0, about), (1, "https://j1.example/x")], JobStats())
    await storage.append_results("j1", [], [(2, about)], JobStats())  # a writer that lost track
    assert await storage.read_links("j1", 0, 10) == ([about, "https://j1.example/x"], 2)


async def test_links_in_first_found_order_with_slices(storage: Storage) -> None:
    await storage.create_job(job())
    links = [f"https://j1.example/{name}" for name in "edcba"]
    await storage.append_results("j1", [], list(enumerate(links)), JobStats())
    assert await storage.read_links("j1", 1, 2) == (links[1:3], 5)


async def test_same_link_kept_per_job(storage: Storage) -> None:
    about = "https://example.com/about"
    for job_id in ("j1", "j2"):
        await storage.create_job(job(job_id))
        await storage.append_results(job_id, [], [(0, about)], JobStats())
    for job_id in ("j1", "j2"):
        assert await storage.read_links(job_id, 0, 10) == ([about], 1)


async def test_very_long_link(storage: Storage) -> None:
    await storage.create_job(job())
    long_link = "https://j1.example/" + "x" * 20_000
    await storage.append_results("j1", [], [(0, long_link)], JobStats())
    await storage.append_results("j1", [], [(1, long_link)], JobStats())
    assert await storage.read_links("j1", 0, 10) == ([long_link], 1)


async def test_mark_interrupted(storage: Storage) -> None:
    await storage.create_job(job("run", status=JobStatus.RUNNING))
    await storage.append_results("run", [(0, page("https://run.example/"))], [], JobStats(pages=1))
    await storage.create_job(job("queued"))
    at = T0 + timedelta(hours=1)
    assert await storage.mark_interrupted("daemon stopped", at) == 1
    stored = await storage.get_job("run")
    assert stored is not None
    assert (stored.status, stored.error, stored.finished_at) == (
        JobStatus.FAILED,
        "daemon stopped",
        at,
    )
    assert (await storage.read_pages("run", 0, 10))[1] == 1  # partial results kept
    queued = await storage.get_job("queued")
    assert queued is not None
    assert queued.status is JobStatus.QUEUED
    assert await storage.mark_interrupted("again", at) == 0


async def test_existing_data_kept_across_reopen(open_db: StorageOpener) -> None:
    first = await open_db()
    await first.create_job(job())
    await first.append_results(
        "j1",
        [(0, page("https://j1.example/", "https://a/"))],
        [(0, "https://a/")],
        JobStats(pages=1),
    )
    await first.aclose()

    second = await open_db()
    assert [j.id for j in await second.list_jobs()] == ["j1"]
    assert (await second.read_pages("j1", 0, 10))[1] == 1
    assert (await second.read_links("j1", 0, 10))[1] == 1


async def test_newer_schema_refused_without_changes(open_db: StorageOpener) -> None:
    first = await open_db()
    assert isinstance(first, SqlStorage)
    await first.create_job(job())
    await first._write([("UPDATE meta SET value = ? WHERE key = ?", [("2", "schema_version")])])
    await first.aclose()

    with pytest.raises(StorageError, match="schema version 2"):
        await open_db()

    # Still version 2 with its data: read it with the newest-schema check bypassed.
    rows = await _raw_read(first, "SELECT value FROM meta WHERE key = ?", ("schema_version",))
    assert rows == [("2",)]


async def _raw_read(
    storage: SqlStorage, sql: str, params: tuple[str, ...]
) -> list[tuple[object, ...]]:
    await storage._connect()
    try:
        return await storage._read(sql, params)
    finally:
        await storage.aclose()


# --- parse cache -----------------------------------------------------------------------


async def test_parse_cache_miss(storage: Storage) -> None:
    assert await storage.get_parsed_links(["nope"]) == {}
    assert await storage.get_parsed_links([]) == {}


async def test_parse_cache_round_trip(storage: Storage) -> None:
    links = ["/b", "/a", "https://other.org/"]
    await storage.put_parsed_links([("k1", links), ("k2", [])], T0)
    assert await storage.get_parsed_links(["k1", "k2", "k3"]) == {"k1": links, "k2": []}


async def test_parse_cache_keeps_first_entry(storage: Storage) -> None:
    await storage.put_parsed_links([("k1", ["/first"])], T0)
    await storage.put_parsed_links([("k1", ["/second"]), ("k1", ["/third"])], T0)
    assert await storage.get_parsed_links(["k1"]) == {"k1": ["/first"]}


async def test_parse_cache_survives_reopen(open_db: StorageOpener) -> None:
    first = await open_db()
    await first.put_parsed_links([("k1", ["/a"])], T0)
    await first.aclose()
    second = await open_db()
    assert await second.get_parsed_links(["k1"]) == {"k1": ["/a"]}


# --- both databases --------------------------------------------------------------------


@needs_postgres
async def test_same_results_from_both_databases(tmp_path: Path) -> None:
    await reset_postgres()
    sqlite = open_storage(f"sqlite:///{tmp_path / 'same.db'}", tmp_path)
    postgres = open_storage(POSTGRES_URL, tmp_path)
    results = []
    for storage in (sqlite, postgres):
        await storage.open()
        try:
            await _run_script(storage)
            results.append(
                (
                    [j.to_dict() for j in await storage.list_jobs()],
                    [j.id for j in await storage.list_jobs(JobStatus.COMPLETED)],
                    await storage.read_pages("a", 0, 100),
                    await storage.read_pages("a", 1, 2),
                    await storage.read_links("a", 0, 100),
                    await storage.read_links("a", 2, 3),
                    await storage.read_links("b", 0, 100),
                    await storage.get_parsed_links(["k1", "k2", "k3"]),
                )
            )
        finally:
            await storage.aclose()
    assert results[0] == results[1]


async def _run_script(storage: Storage) -> None:
    a, b = job("a"), job("b", at=T0 + timedelta(seconds=1))
    await storage.create_job(a)
    await storage.create_job(b)
    pages = [
        page(f"https://a.example/{i}", "https://a.example/", f"https://a.example/{i + 1}")
        for i in range(4)
    ]
    seen: dict[str, int] = {}
    for link in (link for p in pages for link in p.links):
        seen.setdefault(link, len(seen))
    await storage.append_results(
        "a", list(enumerate(pages)), [(n, u) for u, n in seen.items()], JobStats(pages=4)
    )
    await storage.append_results(
        "b", [(0, pages[0])], [(0, "https://a.example/")], JobStats(pages=1)
    )
    a.status, a.finished_at, a.stats = (
        JobStatus.COMPLETED,
        T0 + timedelta(minutes=1),
        JobStats(4, 5, 1, 0, 2),
    )
    await storage.update_job(a)
    await storage.put_parsed_links([("k1", ["/x"]), ("k2", ["/y", "/z"])], T0)
