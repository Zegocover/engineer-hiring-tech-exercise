from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from urllib.parse import urlsplit

import httpx

from .crawler import Crawler
from .extractor import LinkContentExtractor
from .fetcher import Fetcher
from .filters import ExactDomainFilter
from .frontier import Frontier
from .normaliser import DefaultURLNormaliser

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crawler",
        description="Crawl a single web domain, printing each page and the links found on it.",
    )
    parser.add_argument(
        "base_url", help="Starting URL to crawling from, e.g. https://192.168.1.100:3000"
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity, written to stderr (default: WARNING)",
    )
    return parser

def _validate_base_url(base_url: str) -> None:
    parts = urlsplit(base_url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise SystemExit(f"error: base_url must be an absolute http(s) URL, got {base_url!r}")

async def _run(args: argparse.Namespace) -> int:
    domain_filter = ExactDomainFilter(args.base_url)
    frontier = Frontier()
    normaliser = DefaultURLNormaliser()
    content_extractor = LinkContentExtractor(normaliser)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=5.0, read=10, write=10, pool=5.0),
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0"},
    ) as client:
        fetcher = Fetcher(client, max_retries=3)
        crawler = Crawler(
            args.base_url,
            fetcher=fetcher,
            normaliser=normaliser,
            frontier=frontier,
            content_extractor=content_extractor,
            domain_filter=domain_filter,
            concurrency=10,
        )
        stats = await crawler.run()

    print(f"Crawled {stats.pages_crawled} pages, {stats.errors} errors.", file=sys.stderr)
    return 0

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _validate_base_url(args.base_url)
    logging.basicConfig(
        level=args.log_level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return asyncio.run(_run(args))

if __name__ == "__main__":
    raise SystemExit(main())
