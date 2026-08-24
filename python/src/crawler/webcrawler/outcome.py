"""Immutable crawl outcomes and their reporting contract."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Page:
    """Success: an HTML page and the links found on it (document order kept)."""

    url: str
    links: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NonPage:
    """A fetched URL that is not an HTML page."""

    url: str
    reason: str


@dataclass(frozen=True, slots=True)
class Failed:
    """A URL that produced no page: transport error, timeout, non-2xx, or parse error."""

    url: str
    reason: str


type Outcome = Page | NonPage | Failed
type Reporter = Callable[[Outcome], None]
