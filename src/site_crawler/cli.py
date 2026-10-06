"""Command-line entry point."""

import argparse
import asyncio
import sys

from site_crawler.crawler import Crawler, format_page
from site_crawler.url_utils import canonical_url


def build_parser():
    parser = argparse.ArgumentParser(description="Crawl a single host and print the links on each page.")
    parser.add_argument("url", help="Absolute http(s) URL to start from")
    parser.add_argument("--concurrency", type=int, default=10, help="Max in-flight requests (default: 10)")
    parser.add_argument("--timeout", type=float, default=10, help="Per-request timeout in seconds")
    parser.add_argument("--max-pages", type=int, default=None, help="Stop after scheduling this many pages")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.concurrency < 1:
        print("concurrency must be >= 1", file=sys.stderr)
        return 2
    if args.timeout <= 0:
        print("timeout must be > 0", file=sys.stderr)
        return 2
    if canonical_url(args.url) is None:
        print("start URL must be an absolute http(s) URL", file=sys.stderr)
        return 2

    crawler = Crawler(
        concurrency=args.concurrency,
        timeout=args.timeout,
        max_pages=args.max_pages,
    )
    pages = asyncio.run(crawler.crawl(args.url))
    for page in pages:
        print(format_page(page))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
