"""Command-line interface for the web crawler."""

import argparse
import asyncio
import logging
import sys
from urllib.parse import urlparse

from crawler.crawler import Crawler, CrawlStats, PageResult


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def print_page_result(result: PageResult) -> None:
    """Print a single page result to stdout in a readable format."""
    separator = "-" * 80
    print(separator)
    print(f"URL: {result.url}")

    if result.error:
        print(f"  [ERROR] {result.error}")
    elif result.links:
        print(f"  Links ({len(result.links)}):")
        for link in sorted(result.links):
            print(f"    {link}")
    else:
        print("  No links found")


def print_summary(stats: CrawlStats) -> None:
    """Print final crawl summary statistics."""
    print("\n" + "=" * 80)
    print("CRAWL SUMMARY")
    print("=" * 80)
    print(f"  Pages crawled:    {stats.pages_crawled}")
    print(f"  Pages failed:     {stats.pages_failed}")
    print(f"  Total links found: {stats.total_links_found}")
    print(f"  Time elapsed:     {stats.elapsed_seconds:.2f}s")
    print("=" * 80)


def validate_url(url: str) -> str:
    """Validate and normalise the input URL, adding scheme if missing."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    if not parsed.netloc:
        raise argparse.ArgumentTypeError(f"Invalid URL: {url}")

    return url


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="crawl",
        description=(
            "Crawl a website and report all links found on each page. "
            "Only pages on the same domain as the base URL are crawled."
        ),
        epilog="Example: crawl https://example.com --concurrency 20",
    )
    parser.add_argument(
        "url",
        type=validate_url,
        help="The base URL to start crawling from",
    )
    parser.add_argument(
        "-c", "--concurrency",
        type=int,
        default=10,
        help="Maximum number of concurrent requests (default: 10)",
    )
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--user-agent",
        type=str,
        default=None,
        help="Custom User-Agent string",
    )
    parser.add_argument(
        "-m", "--max-pages",
        type=int,
        default=0,
        help="Maximum number of pages to crawl (0 = unlimited, default: 0)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only print the final summary, not individual page results",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    return parser


async def run_crawler(args: argparse.Namespace) -> int:
    """Execute the crawler with parsed arguments. Returns exit code."""
    kwargs: dict = {
        "max_concurrency": args.concurrency,
        "timeout": args.timeout,
        "max_pages": args.max_pages,
    }
    if not args.quiet:
        kwargs["on_page_crawled"] = print_page_result
    if args.user_agent:
        kwargs["user_agent"] = args.user_agent

    crawler = Crawler(args.url, **kwargs)   

    print(f"Starting crawl of: {args.url}")
    print(f"Domain: {crawler.base_domain}")
    print(f"Concurrency: {args.concurrency}")
    print("=" * 80)

    import time
    start = time.perf_counter()

    try:
        await crawler.crawl()
    except KeyboardInterrupt:
        print("\nCrawl interrupted by user.")
        return 130

    stats = crawler.get_stats()
    stats.elapsed_seconds = time.perf_counter() - start
    print_summary(stats)

    return 0 if stats.pages_failed == 0 else 1


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    setup_logging(args.verbose)

    try:
        exit_code = asyncio.run(run_crawler(args))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        exit_code = 130

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
