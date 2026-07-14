"""Tests for the output writers."""

from __future__ import annotations

import io
import json

from crawler.models import PageResult
from crawler.output import JsonWriter, TextWriter, make_writer


def test_text_writer_prints_url_then_indented_links() -> None:
    stream = io.StringIO()
    TextWriter(stream).write(
        PageResult(url="http://x/", links=("http://x/a", "http://x/b"), status_code=200)
    )
    assert stream.getvalue() == "http://x/\n  http://x/a\n  http://x/b\n\n"


def test_text_writer_shows_errors() -> None:
    stream = io.StringIO()
    TextWriter(stream).write(PageResult(url="http://x/y", links=(), error="timeout"))
    assert stream.getvalue() == "http://x/y\n  [error] timeout\n\n"


def test_text_writer_emits_each_page_as_a_single_write() -> None:
    # Atomicity matters under concurrency: one page -> one write call.
    writes: list[str] = []

    class Recorder(io.StringIO):
        def write(self, s: str) -> int:
            writes.append(s)
            return super().write(s)

    TextWriter(Recorder()).write(PageResult(url="http://x/", links=("http://x/a",)))
    assert len(writes) == 1


def test_json_writer_emits_one_object_per_line_with_stable_schema() -> None:
    stream = io.StringIO()
    writer = JsonWriter(stream)
    writer.write(PageResult(url="http://x/", links=("http://x/a",), status_code=200))
    writer.write(PageResult(url="http://x/bad", links=(), error="boom"))

    lines = stream.getvalue().splitlines()
    assert len(lines) == 2

    first = json.loads(lines[0])
    assert first == {
        "url": "http://x/",
        "status": 200,
        "error": None,
        "links": ["http://x/a"],
    }
    second = json.loads(lines[1])
    assert second["error"] == "boom"
    assert second["links"] == []


def test_make_writer_selects_implementation() -> None:
    assert isinstance(make_writer("text"), TextWriter)
    assert isinstance(make_writer("json"), JsonWriter)
