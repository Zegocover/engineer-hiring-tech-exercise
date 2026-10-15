from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PageResult:
    """A crawled page and every normalised link found on it, in document order."""

    url: str
    links: tuple[str, ...]
