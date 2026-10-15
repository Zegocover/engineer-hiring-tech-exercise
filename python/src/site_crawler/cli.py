"""``crawl`` command: results to stdout, logs and the summary to stderr."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from collections.abc import Sequence

from site_crawler.core import Crawler
from site_crawler.interfaces import Writer
from site_crawler.models import DEFAULT_USER_AGENT, ConfigError, CrawlConfig
from site_crawler.writers import JsonLinesWriter, TextWriter

EXIT_OK = 0
EXIT_SEED_FAILED = 1
EXIT_USAGE = 2
EXIT_INTERRUPTED = 130


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def _non_negative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must not be negative")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crawl",
        description="Crawl a single host and print each page with the URLs found on it.",
    )
    parser.add_argument("url", help="absolute http(s) base URL to start from")
    parser.add_argument(
        "-c", "--concurrency", type=_positive_int, default=16, help="parallel requests (16)"
    )
    parser.add_argument("--max-pages", type=_positive_int, help="stop after fetching N pages")
    parser.add_argument(
        "--max-depth", type=_non_negative_int, help="follow links at most N hops from the base URL"
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="per-request timeout in seconds (10)"
    )
    parser.add_argument("--no-robots", action="store_true", help="ignore robots.txt")
    parser.add_argument(
        "--allow-host",
        action="append",
        default=[],
        metavar="PATTERN",
        help="also follow links to this host: docs.example.org, localhost:8001 or *.example.com "
        "(any subdomain); repeatable",
    )
    parser.add_argument(
        "--per-host-concurrency",
        type=_positive_int,
        metavar="N",
        help="at most N parallel requests to any one host (default: no extra limit)",
    )
    parser.add_argument(
        "--format", choices=("text", "jsonl"), default="text", help="output format (text)"
    )
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="User-Agent header")
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="more logging (-v info, -vv debug)"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=(logging.WARNING, logging.INFO, logging.DEBUG)[min(args.verbose, 2)],
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    # Avoid UnicodeEncodeError on consoles with narrow encodings (e.g. cp1252).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")

    try:
        config = CrawlConfig(
            base_url=args.url,
            concurrency=args.concurrency,
            max_pages=args.max_pages,
            max_depth=args.max_depth,
            timeout=args.timeout,
            respect_robots=not args.no_robots,
            user_agent=args.user_agent,
            allowed_hosts=tuple(args.allow_host),
            per_host_concurrency=args.per_host_concurrency,
        )
    except ConfigError as exc:
        print(f"crawl: error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    writer: Writer = JsonLinesWriter() if args.format == "jsonl" else TextWriter()
    started = time.perf_counter()
    try:
        stats = asyncio.run(Crawler(config, writer=writer).run())
    except KeyboardInterrupt:
        print("crawl: interrupted", file=sys.stderr)
        return EXIT_INTERRUPTED
    elapsed = time.perf_counter() - started

    print(
        f"Crawled {stats.pages} pages ({stats.fetched} fetched, {stats.errors} errors, "
        f"{stats.robots_skipped} blocked by robots.txt) in {elapsed:.2f}s",
        file=sys.stderr,
    )
    if not stats.seed_ok:
        print(f"crawl: error: could not fetch base URL {config.base_url}", file=sys.stderr)
        return EXIT_SEED_FAILED
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
