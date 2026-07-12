from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from urllib.parse import urlsplit

import httpx
from httpx_retries import Retry, RetryTransport

from .crawler import Crawler
from .extractor import LinkContentExtractor
from .fetcher import Fetcher
from .filters import ExactDomainFilter
from .frontier import Frontier
from .normaliser import DefaultURLNormaliser
from .robots import load_robots_policy

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crawler",
        description="Crawl a single web domain, printing each page and the links found on it.",
    )
    parser.add_argument(
        "base_url", help="Starting URL to crawling from, e.g. https://192.168.1.100:3000"
    )
    parser.add_argument(
        "--concurrency", type=int, default=10, help="Concurrent worker tasks (default: 10)"
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="Per-request timeout, in seconds (default: 10)"
    )
    parser.add_argument(
        "--max-retries", type=int, default=3, help="Max retry attempts per request (default: 3)"
    )
    parser.add_argument(
        "--max-pages", type=int, default=None, help="Optional cap on total pages crawled"
    )
    parser.add_argument(
        "--max-connections",
        type=int,
        default=10,
        help="Maximum number of concurrent connections that may be established",
    )
    parser.add_argument(
        "--max-keep-alive-connections",
        type=int,
        default=5,
        help="Number of keep-alive connections the pool may hold below --max-connections",
    )
    parser.add_argument(
        "--max-pages", type=int, default=None, help="Optional cap on total pages crawled"
    )
    parser.add_argument(
        "--user-agent", default="zegocrawler/0.1", help="User-Agent header sent with requests"
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

def _create_client(args: argparse.Namespace) -> httpx.AsyncClient:
    retry = Retry(total=args.max_retries, status_forcelist=_RETRYABLE_STATUS)
    return httpx.AsyncClient(
        transport=RetryTransport(retry=retry),
        timeout=httpx.Timeout(connect=5.0, read=args.timeout, write=args.timeout, pool=5.0),
        limits=httpx.Limits(
            max_connections=args.max_connections,
            max_keepalive_connections=args.max_keep_alive_connections,
        ),
        follow_redirects=True,
        headers={"User-Agent": args.user_agent}
    )

async def _run(args: argparse.Namespace) -> int:
    domain_filter = ExactDomainFilter(args.base_url)
    frontier = Frontier()
    normaliser = DefaultURLNormaliser()
    content_extractor = LinkContentExtractor(normaliser)

    async with _create_client(args) as client:
        # Fetching robots.txt is a blocking prerequisite: no worke is done
        # until this await resolves. Retries for
        # this request are handled by the client's RetryTransport, same as any
        # other fetch operation
        robots_fetcher = Fetcher(client)
        robots_policy = await load_robots_policy(args.base_url, robots_fetcher, args.user_agent)

        fetcher = Fetcher(client, min_delay=robots_policy.crawl_delay or 0.0)

        crawler = Crawler(
            args.base_url,
            fetcher=fetcher,
            normaliser=normaliser,
            frontier=frontier,
            content_extractor=content_extractor,
            domain_filter=domain_filter,
            concurrency=args.concurrency,
            robots_policy=robots_policy,
            max_pages=args.max_pages,
        )
        stats = await crawler.run()

    logger.info(
        f"Crawled {stats.pages_crawled} pages, {stats.errors} errors, "
        f"{stats.robots_disallowed} skipped by robots.txt."
    )
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
