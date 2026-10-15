from __future__ import annotations

import io
import json

from site_crawler.models import PageResult
from site_crawler.writers import JsonLinesWriter, TextWriter

RESULTS = [
    PageResult("https://example.com/", ("https://example.com/a", "https://other.org/")),
    PageResult("https://example.com/a", ()),
]


async def test_text_layout() -> None:
    stream = io.StringIO()
    writer = TextWriter(stream)
    for result in RESULTS:
        await writer.write(result)
    await writer.aclose()
    assert stream.getvalue() == (
        "https://example.com/\n"
        "  https://example.com/a\n"
        "  https://other.org/\n"
        "https://example.com/a\n"
    )


async def test_json_lines_each_line_parses() -> None:
    stream = io.StringIO()
    writer = JsonLinesWriter(stream)
    for result in RESULTS:
        await writer.write(result)
    await writer.aclose()
    records = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert records == [
        {"url": "https://example.com/", "links": ["https://example.com/a", "https://other.org/"]},
        {"url": "https://example.com/a", "links": []},
    ]
