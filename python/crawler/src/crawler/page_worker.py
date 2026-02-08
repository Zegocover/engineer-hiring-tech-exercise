from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageResult:
    url: str
    links: list[str]
    status: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class WorkItem:
    url: str
    attempts: int = 0


class PageWorker:
    def __init__(self, *, timeout: float = 10.0, retries: int = 1) -> None:
        self.timeout = timeout
        self.retries = retries

    async def fetch(self, url: str) -> PageResult:
        return PageResult(url=url, links=[])
