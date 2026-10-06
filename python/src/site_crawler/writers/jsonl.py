from __future__ import annotations

import json
import sys
from typing import TextIO

from site_crawler.models import PageResult


class JsonLinesWriter:
    """One JSON object per page per line: ``{"url": ..., "links": [...]}``."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream if stream is not None else sys.stdout

    async def write(self, result: PageResult) -> None:
        record = {"url": result.url, "links": list(result.links)}
        self._stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def aclose(self) -> None:
        self._stream.flush()
