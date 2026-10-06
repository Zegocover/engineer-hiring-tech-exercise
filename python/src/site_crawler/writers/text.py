from __future__ import annotations

import sys
from typing import TextIO

from site_crawler.models import PageResult


class TextWriter:
    """Human-readable output: the page URL, then each link indented below it."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream if stream is not None else sys.stdout

    async def write(self, result: PageResult) -> None:
        lines = [result.url, *(f"  {link}" for link in result.links)]
        self._stream.write("\n".join(lines) + "\n")

    async def aclose(self) -> None:
        self._stream.flush()
