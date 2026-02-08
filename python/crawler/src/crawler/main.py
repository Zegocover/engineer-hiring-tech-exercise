from __future__ import annotations

import argparse
import asyncio
from typing import Callable

from crawler.site_crawler import SiteCrawler


def _bounded_int(min_value: int, max_value: int) -> Callable[[str], int]:
    def _parse(value: str) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("must be an integer") from exc
        if parsed < min_value or parsed > max_value:
            raise argparse.ArgumentTypeError(
                f"must be between {min_value} and {max_value}"
            )
        return parsed

    return _parse


def _bounded_float(min_value: float, max_value: float) -> Callable[[str], float]:
    def _parse(value: str) -> float:
        try:
            parsed = float(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("must be a number") from exc
        if parsed < min_value or parsed > max_value:
            raise argparse.ArgumentTypeError(
                f"must be between {min_value} and {max_value}"
            )
        return parsed

    return _parse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Single-domain, async web crawler.",
    )
    parser.add_argument("url", help="Base URL to crawl (must include scheme).")
    parser.add_argument(
        "--output",
        help="Write output to a file instead of stdout.",
    )
    parser.add_argument(
        "--batch-size",
        type=_bounded_int(1, 10),
        default=10,
        help="Maximum concurrent requests per batch.",
    )
    parser.add_argument(
        "--max-urls",
        type=_bounded_int(1, 1000),
        default=None,
        help="Maximum number of URLs to visit.",
    )
    parser.add_argument(
        "--timeout",
        type=_bounded_float(0.0, 10.0),
        default=5.0,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--retries",
        type=_bounded_int(0, 3),
        default=1,
        help="Number of retries for transient failures.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    output_format = "json" if args.output else "text"

    crawler = SiteCrawler(
        args.url,
        batch_size=args.batch_size,
        max_urls=args.max_urls,
        timeout=args.timeout,
        retries=args.retries,
        output=args.output,
        output_format=output_format,
    )
    asyncio.run(crawler.crawl())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
