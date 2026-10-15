from site_crawler.models import CrawlConfig

from crawler_api.jobs import CrawlJob, InMemoryJobStore, JobStatus


def make_job(job_id: str) -> CrawlJob:
    return CrawlJob(id=job_id, config=CrawlConfig(f"https://{job_id}.example/"))


def test_new_job_is_running_and_empty() -> None:
    job = make_job("a")
    assert job.status is JobStatus.RUNNING
    assert job.finished_at is None
    assert job.pages == []
    assert job.links == []


def test_get_unknown_returns_none() -> None:
    store = InMemoryJobStore()
    store.add(make_job("a"))
    assert store.get("missing") is None
    assert store.get("a") is not None


def test_list_recent_first() -> None:
    store = InMemoryJobStore()
    for job_id in ("a", "b", "c"):
        store.add(make_job(job_id))
    assert [job.id for job in store.list_recent_first()] == ["c", "b", "a"]
