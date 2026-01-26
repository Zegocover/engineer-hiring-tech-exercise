"""Shared data models for crawler state and results."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CrawlItem:
    """Represents a URL scheduled for crawling."""

    url: str
    depth: int
    attempts: int = 0
