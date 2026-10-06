from __future__ import annotations

from typing import Protocol

from site_crawler.models import PageResult


class Writer(Protocol):
    """Receives page results one at a time, then is closed once at the end."""

    async def write(self, result: PageResult) -> None: ...

    async def aclose(self) -> None: ...
