"""Responsible for orchestration of the application layers."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import httpx

from crawler.config import DEFAULT_OUTPUT_DIR, DEFAULT_REQUEST_TIMEOUT, USER_AGENT
from crawler.crawler import Crawler, CrawlResult
from crawler.output import write_result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl a website and report its in-domain pages."
    )
    parser.add_argument("url", help="Starting URL to crawl, e.g. https://example.com")
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Maximum time in seconds to spend crawling (default: 30)",
    )
    parser.add_argument(
        "--max-concurrent-requests",
        type=int,
        default=10,
        help="Maximum number of in-flight requests at a time (default: 10)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show per-page crawl progress logs",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for per-domain JSON results (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print a human-readable summary instead of the raw result",
    )
    return parser.parse_args(argv)


def format_pretty(result: CrawlResult) -> str:
    """Renders a CrawlResult as a readable, grouped summary."""
    status = "completed" if result.completed else "timed out"
    lines = [f"Crawl {status} — {len(result.visited)} page(s) visited", ""]

    lines.append(f"Visited ({len(result.visited)}):")
    for visited_url in sorted(result.visited):
        lines.append(f"  - {visited_url}")

    lines.append("")
    lines.append(
        f"Found URLs by domain ({len(result.found_urls_by_domain)} domain(s)):"
    )
    for domain in sorted(result.found_urls_by_domain):
        urls = result.found_urls_by_domain[domain]
        lines.append(f"  {domain} ({len(urls)}):")
        for found_url in sorted(urls):
            lines.append(f"    - {found_url}")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="[%(levelname)s] %(message)s",
    )
    asyncio.run(_run_crawler(args))


async def _run_crawler(args: argparse.Namespace) -> None:
    try:
        limits = httpx.Limits(
            max_connections=args.max_concurrent_requests,
            max_keepalive_connections=args.max_concurrent_requests,
        )
        async with httpx.AsyncClient(
            limits=limits,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=DEFAULT_REQUEST_TIMEOUT,
        ) as client:
            result = await Crawler().crawl(
                client,
                args.url,
                timeout=args.timeout,
                max_concurrency=args.max_concurrent_requests,
            )
    except httpx.HTTPError as exc:
        print(f"Error: {exc}")
        return
    # Results go to a file first, then we print. The file is the artefact a
    # datastore would hold; stdout is just a view onto it.
    try:
        output_path = write_result(result, args.url, output_dir=args.output_dir)
    except OSError as exc:
        print(f"Could not write results: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if args.pretty:
        print(format_pretty(result))
    else:
        print(output_path.read_text(encoding="utf-8"), end="")

    print(f"\nWrote {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
