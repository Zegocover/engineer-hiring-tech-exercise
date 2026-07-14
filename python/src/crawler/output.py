"""Output sinks behind an ``OutputWriter`` protocol, keeping I/O out of the crawler."""

from __future__ import annotations

import json
import sys
from typing import Protocol, TextIO

from crawler.config import OutputFormat
from crawler.models import PageResult


class OutputWriter(Protocol):
    def write(self, page: PageResult) -> None: ...


class TextWriter:
    """Human-readable output: the page URL followed by its indented links."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream if stream is not None else sys.stdout

    def write(self, page: PageResult) -> None:
        lines = [page.url]
        if page.error is not None:
            lines.append(f"  [error] {page.error}")
        lines.extend(f"  {link}" for link in page.links)
        # One write per page so blocks don't interleave under concurrency.
        self._stream.write("\n".join(lines) + "\n\n")


class JsonWriter:
    """Optional writer for machine-readable JSON output (one JSON object per line)."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream if stream is not None else sys.stdout

    def write(self, page: PageResult) -> None:
        record: dict[str, object] = {
            "url": page.url,
            "status": page.status_code,
            "error": page.error,
            "links": list(page.links),
        }
        self._stream.write(json.dumps(record) + "\n")


def make_writer(output_format: OutputFormat, stream: TextIO | None = None) -> OutputWriter:
    if output_format == "json":
        return JsonWriter(stream)
    return TextWriter(stream)
