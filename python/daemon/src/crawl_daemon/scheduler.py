"""Queues crawl jobs and runs a bounded number of them at once.

Jobs wait in a FIFO queue and ``max_parallel_jobs`` workers take them in
order. Queued and running jobs are held in memory as well as in storage;
storage is the record for everything else, including after a restart.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from site_crawler import Crawler
from site_crawler.interfaces import Fetcher
from site_crawler.models import ConfigError, CrawlConfig, PageResult

from crawl_daemon.components import CachingParser, ParseCache, SharedClientFetcher, StorageWriter
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
from crawl_daemon.settings import Settings
from crawl_daemon.storage import Storage

logger = logging.getLogger(__name__)

FetcherFactory = Callable[[], Fetcher]
"""Makes the fetcher a job's :class:`SharedClientFetcher` wraps."""

INTERRUPTED = "the daemon stopped before the crawl finished"


@dataclass(eq=False, slots=True)
class _Active:
    record: JobRecord
    crawler: Crawler
    cache: ParseCache
    task: asyncio.Task[object]
    cancel_requested: bool = False
    done: asyncio.Event = field(default_factory=asyncio.Event)

    def live_stats(self) -> JobStats:
        return JobStats.from_crawl(self.crawler.stats, self.cache.hits)


class JobScheduler:
    def __init__(
        self,
        settings: Settings,
        storage: Storage,
        fetcher_factory: FetcherFactory,
        *,
        flush_interval: float = 0.5,
    ) -> None:
        self._settings = settings
        self._storage = storage
        self._fetcher_factory = fetcher_factory
        self._flush_interval = flush_interval
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._queued: dict[str, JobRecord] = {}
        self._active: dict[str, _Active] = {}
        self._workers: list[asyncio.Task[None]] = []
        self._stopping = False
        self._last_submitted: datetime | None = None

    # --- lifecycle ---------------------------------------------------------------------

    async def start(self) -> int:
        """Recover jobs left by an earlier run, then start the workers.

        Jobs a crashed daemon left ``running`` are failed; queued jobs run in
        submission order. Returns how many jobs were failed.
        """
        interrupted = await self._storage.mark_interrupted(INTERRUPTED, utcnow())
        if interrupted:
            logger.warning("failed %d job(s) interrupted by an earlier daemon", interrupted)
        jobs = await self._storage.list_jobs()
        if jobs:
            self._last_submitted = jobs[0].submitted_at
        for record in reversed([job for job in jobs if job.status is JobStatus.QUEUED]):
            self._enqueue(record)
        self._workers = [
            asyncio.create_task(self._worker(), name=f"job-worker-{i}")
            for i in range(self._settings.max_parallel_jobs)
        ]
        return interrupted

    async def shutdown(self) -> None:
        """Cancel running jobs and wait for them; queued jobs stay queued for the next run."""
        self._stopping = True
        active = list(self._active.values())
        for job in active:
            job.cancel_requested = True
            job.task.cancel()
        await asyncio.gather(*(job.done.wait() for job in active))
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []

    @property
    def running_count(self) -> int:
        return len(self._active)

    @property
    def queued_count(self) -> int:
        return len(self._queued)

    # --- jobs --------------------------------------------------------------------------

    async def submit(
        self,
        url: str,
        *,
        max_pages: int | None = None,
        max_depth: int | None = None,
        concurrency: int | None = None,
        per_host_concurrency: int | None = None,
        respect_robots: bool = True,
        allowed_hosts: Sequence[str] = (),
    ) -> JobRecord:
        """Validate a job and queue it. Nothing is stored for an invalid job."""
        if self._stopping:
            raise ConflictError("the daemon is stopping")
        settings = self._settings
        if max_pages is None:
            max_pages = settings.default_max_pages
        elif max_pages > settings.max_pages_limit:
            raise InvalidRequestError(f"max_pages must be at most {settings.max_pages_limit}")
        if concurrency is None:
            concurrency = settings.default_concurrency
        elif concurrency > settings.max_concurrency:
            raise InvalidRequestError(f"concurrency must be at most {settings.max_concurrency}")
        if per_host_concurrency is not None and per_host_concurrency > settings.max_concurrency:
            raise InvalidRequestError(
                f"per_host_concurrency must be at most {settings.max_concurrency}"
            )
        try:
            config = CrawlConfig(
                base_url=url,
                concurrency=concurrency,
                max_pages=max_pages,
                max_depth=max_depth,
                respect_robots=respect_robots,
                allowed_hosts=tuple(allowed_hosts),
                per_host_concurrency=per_host_concurrency,
            )
        except ConfigError as exc:
            raise InvalidRequestError(str(exc)) from exc

        record = JobRecord(
            id=uuid.uuid4().hex,
            url=config.base_url,
            limits=JobLimits.from_config(config),
            status=JobStatus.QUEUED,
            submitted_at=self._next_submission_time(),
        )
        await self._storage.create_job(record)
        self._enqueue(record)
        return record

    async def get(self, job_id: str) -> JobRecord:
        if job_id in self._queued:
            return self._queued[job_id]
        if job_id in self._active:
            active = self._active[job_id]
            active.record.stats = active.live_stats()
            return active.record
        record = await self._storage.get_job(job_id)
        if record is None:
            raise NotFoundError(f"no job with id {job_id}")
        return record

    async def list_jobs(self, status: JobStatus | None = None) -> list[JobRecord]:
        records = await self._storage.list_jobs(status)
        for record in records:
            if record.id in self._active:
                record.stats = self._active[record.id].live_stats()
        return records

    async def pages(self, job_id: str, offset: int, limit: int) -> tuple[list[PageResult], int]:
        await self.get(job_id)
        return await self._storage.read_pages(job_id, offset, limit)

    async def links(self, job_id: str, offset: int, limit: int) -> tuple[list[str], int]:
        await self.get(job_id)
        return await self._storage.read_links(job_id, offset, limit)

    async def cancel(self, job_id: str) -> JobRecord:
        """Cancel a queued or running job; a running one is waited for until it has stopped."""
        record = self._queued.pop(job_id, None)
        if record is not None:
            record.status = JobStatus.CANCELLED
            record.finished_at = utcnow()
            await self._storage.update_job(record)
            return record
        active = self._active.get(job_id)
        if active is not None:
            if active.task.done():  # already finishing on its own: report how it ended
                await active.done.wait()
                raise ConflictError(f"job {job_id} is already {active.record.status}")
            active.cancel_requested = True
            active.task.cancel()
            await active.done.wait()
            return active.record
        record = await self.get(job_id)
        raise ConflictError(f"job {job_id} is already {record.status}")

    # --- running -----------------------------------------------------------------------

    def _enqueue(self, record: JobRecord) -> None:
        self._queued[record.id] = record
        self._queue.put_nowait(record.id)

    def _next_submission_time(self) -> datetime:
        """Now, but always later than the last job, so "newest first" is well defined."""
        now = utcnow()
        if self._last_submitted is not None and now <= self._last_submitted:
            now = self._last_submitted + timedelta(microseconds=1)
        self._last_submitted = now
        return now

    async def _worker(self) -> None:
        while True:
            job_id = await self._queue.get()
            if self._stopping:
                return
            # No await between taking the id and claiming the job, so a cancel
            # either removed it from _queued already or will find it active.
            record = self._queued.pop(job_id, None)
            if record is not None:
                await self._run(record)

    async def _run(self, record: JobRecord) -> None:
        settings = self._settings
        limits = record.limits
        config = CrawlConfig(
            base_url=record.url,
            concurrency=limits.concurrency,
            max_pages=limits.max_pages,
            max_depth=limits.max_depth,
            timeout=settings.request_timeout,
            respect_robots=limits.respect_robots,
            user_agent=settings.user_agent,
            allowed_hosts=limits.allowed_hosts,
            per_host_concurrency=limits.per_host_concurrency,
        )
        cache = ParseCache(enabled=settings.parse_cache)
        writer = StorageWriter(
            self._storage,
            record.id,
            stats=lambda: active.live_stats(),  # only called once the crawl runs
            cache=cache,
            flush_interval=self._flush_interval,
        )
        crawler = Crawler(
            config,
            fetcher=SharedClientFetcher(
                self._fetcher_factory(), storage=self._storage, cache=cache
            ),
            parser=CachingParser(cache),
            writer=writer,
        )
        record.status = JobStatus.RUNNING
        record.started_at = utcnow()
        task: asyncio.Task[object] = asyncio.create_task(crawler.run(), name=f"crawl-{record.id}")
        active = _Active(record, crawler, cache, task)
        self._active[record.id] = active
        try:
            try:
                await self._storage.update_job(record)
            except Exception:
                logger.exception("could not record that job %s started", record.id)
            await asyncio.wait([task])
            write_error: BaseException | None = None
            try:
                await writer.aclose()  # usually already closed by the crawler: a no-op
            except Exception as exc:
                write_error = exc
            self._finish(active, write_error)
            try:
                await self._storage.update_job(record)
            except Exception:
                logger.exception("could not record the final status of job %s", record.id)
        finally:
            del self._active[record.id]
            active.done.set()

    def _finish(self, active: _Active, write_error: BaseException | None) -> None:
        record, task = active.record, active.task
        record.stats = active.live_stats()
        record.finished_at = utcnow()
        if active.cancel_requested or task.cancelled():
            record.status = JobStatus.CANCELLED
        elif (exc := task.exception()) is not None:
            logger.error("job %s failed", record.id, exc_info=exc)
            record.status = JobStatus.FAILED
            record.error = f"{type(exc).__name__}: {exc}"
        elif write_error is not None:
            record.status = JobStatus.FAILED
            record.error = f"{type(write_error).__name__}: {write_error}"
        elif active.crawler.stats.seed_ok:
            record.status = JobStatus.COMPLETED
        else:
            record.status = JobStatus.FAILED
            record.error = f"could not fetch base URL {record.url}"
