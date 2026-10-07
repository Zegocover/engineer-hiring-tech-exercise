"""Crawl endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from crawler_api.jobs import CrawlJob
from crawler_api.schemas import (
    CrawlDetail,
    CrawlRequest,
    CrawlStatus,
    CrawlSummary,
    LinkList,
    Page,
    PageList,
)
from crawler_api.service import CrawlService, JobNotFoundError, JobNotRunningError

router = APIRouter(prefix="/crawls", tags=["crawls"])


def get_service(request: Request) -> CrawlService:
    service: CrawlService = request.app.state.service
    return service


Service = Annotated[CrawlService, Depends(get_service)]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=1000)]


def get_job(job_id: str, service: Service) -> CrawlJob:
    try:
        return service.get(job_id)
    except JobNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"crawl {job_id} not found") from None


Job = Annotated[CrawlJob, Depends(get_job)]


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def start_crawl(body: CrawlRequest, service: Service, response: Response) -> CrawlSummary:
    """Start a crawl in the background. Poll its ``/status`` to follow it."""
    job = service.start(
        body.url,
        max_pages=body.max_pages,
        max_depth=body.max_depth,
        concurrency=body.concurrency,
        respect_robots=body.respect_robots,
    )
    response.headers["Location"] = f"/crawls/{job.id}"
    return CrawlSummary.of(job)


@router.get("")
async def list_crawls(service: Service) -> list[CrawlSummary]:
    """Every crawl held by the service, most recently started first."""
    return [CrawlSummary.of(job) for job in service.list()]


@router.get("/{job_id}")
async def get_crawl(job: Job) -> CrawlDetail:
    return CrawlDetail.of(job)


@router.get("/{job_id}/status")
async def get_crawl_status(job: Job) -> CrawlStatus:
    return CrawlStatus.of(job)


@router.get("/{job_id}/pages")
async def get_crawl_pages(job: Job, offset: Offset = 0, limit: Limit = 100) -> PageList:
    """Pages in the order the crawl reported them, each with its links."""
    items = [
        Page(url=page.url, links=list(page.links)) for page in job.pages[offset : offset + limit]
    ]
    return PageList(total=len(job.pages), offset=offset, limit=limit, items=items)


@router.get("/{job_id}/links")
async def get_crawl_links(job: Job, offset: Offset = 0, limit: Limit = 100) -> LinkList:
    """Distinct links found on any page, in first-seen order, followed or not."""
    return LinkList(
        total=len(job.links), offset=offset, limit=limit, items=job.links[offset : offset + limit]
    )


@router.delete("/{job_id}")
async def cancel_crawl(job: Job, service: Service) -> CrawlDetail:
    """Cancel a running crawl. The pages it already found are kept."""
    try:
        await service.cancel(job.id)
    except JobNotRunningError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    return CrawlDetail.of(job)
