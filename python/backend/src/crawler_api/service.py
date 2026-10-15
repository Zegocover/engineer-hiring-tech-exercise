"""Starts crawls as background tasks and tracks them as jobs.

The service knows nothing about HTTP: routes translate its errors into
status codes.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable, Sequence

from site_crawler import Crawler
from site_crawler.interfaces import Fetcher
from site_crawler.models import CrawlConfig

from crawler_api.adapters import JobWriter, StdlibHtmlParser
from crawler_api.jobs import CrawlJob, InMemoryJobStore, JobStatus, JobStore, utcnow
from crawler_api.settings import Settings

logger = logging.getLogger(__name__)

FetcherFactory = Callable[[], Fetcher]


class LimitError(ValueError):
    """A requested limit exceeds what the service allows."""


class JobNotFoundError(LookupError):
    pass


class JobNotRunningError(RuntimeError):
    def __init__(self, job: CrawlJob) -> None:
        super().__init__(f"crawl {job.id} is already {job.status}")
        self.job = job


class CrawlService:
    def __init__(
        self,
        settings: Settings,
        fetcher_factory: FetcherFactory,
        store: JobStore | None = None,
    ) -> None:
        self._settings = settings
        self._fetcher_factory = fetcher_factory
        self._store: JobStore = store if store is not None else InMemoryJobStore()

    def start(
        self,
        url: str,
        *,
        max_pages: int | None = None,
        max_depth: int | None = None,
        concurrency: int | None = None,
        per_host_concurrency: int | None = None,
        respect_robots: bool = True,
        allowed_hosts: Sequence[str] = (),
    ) -> CrawlJob:
        """Validate the request, then start the crawl in the background.

        Raises :class:`LimitError` or :class:`site_crawler.ConfigError` before
        anything is stored when the request is invalid.
        """
        settings = self._settings
        if max_pages is None:
            max_pages = settings.default_max_pages
        elif max_pages > settings.max_pages_limit:
            raise LimitError(f"max_pages must be at most {settings.max_pages_limit}")
        if concurrency is None:
            concurrency = settings.default_concurrency
        elif concurrency > settings.max_concurrency:
            raise LimitError(f"concurrency must be at most {settings.max_concurrency}")
        if per_host_concurrency is not None and per_host_concurrency > settings.max_concurrency:
            raise LimitError(f"per_host_concurrency must be at most {settings.max_concurrency}")

        config = CrawlConfig(
            base_url=url,
            concurrency=concurrency,
            max_pages=max_pages,
            max_depth=max_depth,
            timeout=settings.request_timeout,
            respect_robots=respect_robots,
            user_agent=settings.user_agent,
            allowed_hosts=tuple(allowed_hosts),
            per_host_concurrency=per_host_concurrency,
        )
        job = CrawlJob(id=uuid.uuid4().hex, config=config)
        crawler = Crawler(
            config,
            fetcher=self._fetcher_factory(),
            parser=StdlibHtmlParser(),
            writer=JobWriter(job),
        )
        job.stats = crawler.stats
        self._store.add(job)
        job.task = asyncio.create_task(self._run(job, crawler), name=f"crawl-{job.id}")
        return job

    @staticmethod
    async def _run(job: CrawlJob, crawler: Crawler) -> None:
        try:
            stats = await crawler.run()
        except asyncio.CancelledError:
            job.status = JobStatus.CANCELLED  # the service cancelled it: not an error
        except Exception as exc:
            logger.exception("crawl %s failed", job.id)
            job.status = JobStatus.FAILED
            job.error = f"{type(exc).__name__}: {exc}"
        else:
            if stats.seed_ok:
                job.status = JobStatus.COMPLETED
            else:
                job.status = JobStatus.FAILED
                job.error = f"could not fetch base URL {job.config.base_url}"
        finally:
            job.finished_at = utcnow()

    def get(self, job_id: str) -> CrawlJob:
        job = self._store.get(job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        return job

    def list(self) -> list[CrawlJob]:
        return self._store.list_recent_first()

    async def cancel(self, job_id: str) -> CrawlJob:
        """Cancel a running crawl and wait until it has stopped."""
        job = self.get(job_id)
        if job.status is not JobStatus.RUNNING:
            raise JobNotRunningError(job)
        await self._stop(job)
        return job

    async def shutdown(self) -> None:
        """Cancel every running crawl and wait for them to stop."""
        running = [
            job for job in self._store.list_recent_first() if job.status is JobStatus.RUNNING
        ]
        await asyncio.gather(*(self._stop(job) for job in running))

    @staticmethod
    async def _stop(job: CrawlJob) -> None:
        if job.task is not None:
            job.task.cancel()
            # wait() instead of awaiting the task: it never re-raises the cancellation.
            await asyncio.wait([job.task])
        # A task cancelled before its first step never reaches _run's handlers.
        if job.status is JobStatus.RUNNING:
            job.status = JobStatus.CANCELLED
            job.finished_at = utcnow()
