"""Command-line adapter: argument handling, reporting, and exit codes."""

from __future__ import annotations

import asyncio
import sys
from typing import assert_never

from pydantic import ValidationError

from .config import Config
from .web import urls
from .webcrawler.crawl import crawl
from .webcrawler.outcome import Failed, NonPage, Outcome, Page, Reporter


def make_reporter() -> Reporter:
    """Write each ``Page`` block to stdout and failures to stderr; ignore non-pages."""

    def report(outcome: Outcome) -> None:
        match outcome:
            case Page(url=url, links=links):
                lines = (url, *dict.fromkeys(links))
                sys.stdout.write("".join(f"{line}\n" for line in lines) + "\n")
            case NonPage():
                pass
            case Failed(url=url, reason=reason):
                sys.stderr.write(f"error: {url}: {reason}\n")
            case _ as unreachable:
                assert_never(unreachable)

    return report


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        sys.stderr.write("usage: python -m crawler <url>\n")
        return 2
    base_url = args[0]
    try:
        config = Config()
    except ValidationError as error:
        for err in error.errors():
            field = ".".join(str(part) for part in err["loc"]) or "config"
            sys.stderr.write(f"error: {field}: {err['msg']}\n")
        return 2
    try:
        outcome = asyncio.run(crawl(base_url, config, make_reporter()))
    except urls.InvalidBaseURLError as error:
        sys.stderr.write(f"error: {error}\n")
        return 2
    return 1 if isinstance(outcome, Failed) else 0
