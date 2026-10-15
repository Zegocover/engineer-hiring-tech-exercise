import json
from datetime import UTC, datetime

import pytest
from site_crawler.models import CrawlConfig, CrawlStats

from crawl_daemon.models import (
    ERRORS_BY_CODE,
    ConflictError,
    JobLimits,
    JobRecord,
    JobStats,
    JobStatus,
    NotFoundError,
)


def make_record() -> JobRecord:
    return JobRecord(
        id="abc",
        url="https://example.com/",
        limits=JobLimits(
            max_pages=10,
            concurrency=4,
            max_depth=2,
            per_host_concurrency=1,
            respect_robots=False,
            allowed_hosts=("*.example.com",),
        ),
        status=JobStatus.COMPLETED,
        submitted_at=datetime(2026, 1, 2, 3, 4, 5, 6, tzinfo=UTC),
        started_at=datetime(2026, 1, 2, 3, 4, 6, tzinfo=UTC),
        finished_at=datetime(2026, 1, 2, 3, 5, 0, tzinfo=UTC),
        error=None,
        stats=JobStats(pages=3, fetched=4, errors=1, robots_skipped=0, parse_cache_hits=2),
    )


def test_record_round_trips_through_json() -> None:
    record = make_record()
    data = json.loads(json.dumps(record.to_dict()))
    assert JobRecord.from_dict(data) == record


def test_record_dict_shape() -> None:
    data = make_record().to_dict()
    assert data["status"] == "completed"
    assert data["limits"]["allowed_hosts"] == ["*.example.com"]
    assert data["stats"]["parse_cache_hits"] == 2
    assert data["submitted_at"] == "2026-01-02T03:04:05.000006+00:00"


def test_queued_record_has_no_times() -> None:
    record = JobRecord(
        id="q",
        url="https://example.com/",
        limits=JobLimits(max_pages=1, concurrency=1),
        status=JobStatus.QUEUED,
        submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    data = record.to_dict()
    assert data["started_at"] is None
    assert data["finished_at"] is None
    assert JobRecord.from_dict(data) == record


def test_limits_from_config() -> None:
    config = CrawlConfig("https://example.com/", max_pages=5, concurrency=3, max_depth=1)
    limits = JobLimits.from_config(config)
    assert limits == JobLimits(max_pages=5, concurrency=3, max_depth=1)
    with pytest.raises(ValueError, match="budget"):
        JobLimits.from_config(CrawlConfig("https://example.com/"))


def test_stats_from_crawl() -> None:
    crawl = CrawlStats(pages=2, fetched=3, errors=1, robots_skipped=4)
    assert JobStats.from_crawl(crawl, 1) == JobStats(2, 3, 1, 4, 1)


def test_finished_statuses() -> None:
    assert [s for s in JobStatus if s.finished] == [
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    ]


def test_error_codes() -> None:
    assert ERRORS_BY_CODE["not_found"] is NotFoundError
    assert ERRORS_BY_CODE["conflict"] is ConflictError
    assert set(ERRORS_BY_CODE) == {
        "invalid_request",
        "unauthorized",
        "not_found",
        "conflict",
        "internal",
    }
