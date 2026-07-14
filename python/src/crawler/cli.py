"""Command-line entry point: parse args into a CrawlConfig, wire deps, run."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time

from crawler import __version__
from crawler.config import CrawlConfig
from crawler.crawler import DEFAULT_CONCURRENCY, Crawler
from crawler.extractor import LinkExtractor
from crawler.fetcher import DEFAULT_TIMEOUT, DEFAULT_USER_AGENT, HttpxFetcher
from crawler.output import make_writer
from crawler.url import get_host

logger = logging.getLogger("crawler")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crawl",
        description="Crawl a single domain and print each page with the links found on it.",
    )
    parser.add_argument(
        "url",
        help="Base URL to start crawling. The scheme is optional and defaults to https.",
    )
    parser.add_argument(
        "-c",
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Number of pages to fetch in parallel (default: {DEFAULT_CONCURRENCY}).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Per-request timeout in seconds (default: {DEFAULT_TIMEOUT}).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Stop after crawling this many pages (default: no limit).",
    )
    parser.add_argument(
        "--include-subdomains",
        action="store_true",
        help="Also crawl subdomains of the base host (off by default).",
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent header to send.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit JSON Lines instead of human-readable text.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Log each page as it is crawled (to stderr).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        stream=sys.stderr,
        format="%(levelname)s %(message)s",
    )

    base_url = _ensure_scheme(args.url.strip())
    if get_host(base_url) is None:
        print(f"error: not a valid URL: {args.url!r}", file=sys.stderr)
        return 2
    if args.concurrency < 1:
        print("error: --concurrency must be >= 1", file=sys.stderr)
        return 2
    if args.max_pages is not None and args.max_pages < 1:
        print("error: --max-pages must be >= 1", file=sys.stderr)
        return 2

    config = CrawlConfig(
        base_url=base_url,
        concurrency=args.concurrency,
        timeout=args.timeout,
        max_pages=args.max_pages,
        user_agent=args.user_agent,
        include_subdomains=args.include_subdomains,
        output_format="json" if args.as_json else "text",
    )

    try:
        return asyncio.run(_crawl(config))
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


async def _crawl(config: CrawlConfig) -> int:
    writer = make_writer(config.output_format)
    crawled = 0
    errors = 0
    start = time.perf_counter()

    async with HttpxFetcher(
        timeout=config.timeout,
        user_agent=config.user_agent,
        max_bytes=config.max_bytes,
    ) as fetcher:
        crawler = Crawler(
            fetcher,
            LinkExtractor(),
            base_url=config.base_url,
            concurrency=config.concurrency,
            max_pages=config.max_pages,
            include_subdomains=config.include_subdomains,
        )
        async for page in crawler.crawl():
            writer.write(page)
            crawled += 1
            if page.error is not None or (page.status_code is not None and page.status_code >= 400):
                errors += 1
            logger.info("%s (%d links)", page.url, len(page.links))

    elapsed = time.perf_counter() - start
    # Summary to stderr; results went to stdout, keeping it clean for piping.
    print(
        f"crawled {crawled} page(s), {errors} error(s) in {elapsed:.2f}s",
        file=sys.stderr,
    )
    return 0


def _ensure_scheme(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url
