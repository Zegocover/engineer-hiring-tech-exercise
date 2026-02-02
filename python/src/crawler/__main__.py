"""CLI entry point for the web crawler."""

import argparse
import asyncio
import logging
import sys

from .crawler import Crawler, CrawlerConfig, CrawlResult
from .url_utils import is_valid_http_url


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="crawl",
        description="Crawl a website and print all discovered URLs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  crawl https://example.com
  crawl https://example.com -c 20 -t 60
  crawl https://example.com --max-pages 100
        """,
    )
    parser.add_argument(
        "url",
        help="Base URL to start crawling from",
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
        "-m", "--max-pages",
        type=int,
        default=None,
        help="Maximum number of pages to crawl (default: unlimited)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only output URLs, no formatting",
    )
    return parser.parse_args()


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


def print_result(result: CrawlResult, quiet: bool) -> None:
    """Print crawl result to stdout.

    Args:
        result: The crawl result to print.
        quiet: If True, output only URLs without formatting.
    """
    if quiet:
        # Simple format: just URLs
        print(result.url)
        for link in result.links:
            print(f"  {link}")
    else:
        # Formatted output
        if result.error:
            print(f"[Error] {result.url}")
            print(f"        {result.error}")
        else:
            print(f"[Page] {result.url}")
            for link in result.links:
                print(f"  -> {link}")
        print()  # Blank line between pages


async def run() -> int:
    """Main async entry point."""
    args = parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Validate URL
    if not is_valid_http_url(args.url):
        print(f"Error: Invalid URL '{args.url}'", file=sys.stderr)
        print("URL must start with http:// or https://", file=sys.stderr)
        return 1

    # Configure crawler
    config = CrawlerConfig(
        concurrency=args.concurrency,
        timeout=args.timeout,
        max_pages=args.max_pages,
    )

    # Print header
    if not args.quiet:
        print(f"Crawling: {args.url}")
        print(f"Concurrency: {config.concurrency}, Timeout: {config.timeout}s")
        if config.max_pages:
            print(f"Max pages: {config.max_pages}")
        print("-" * 60)
        print()

    # Create callback for streaming output
    def on_page_crawled(result: CrawlResult) -> None:
        print_result(result, args.quiet)

    # Run crawler
    crawler = Crawler(args.url, config=config, on_page_crawled=on_page_crawled)

    try:
        results = await crawler.crawl()
    except KeyboardInterrupt:
        print("\nCrawl interrupted by user", file=sys.stderr)
        return 130

    # Print summary
    if not args.quiet:
        print("-" * 60)
        total_pages = len(results)
        errors = sum(1 for r in results if r.error)
        total_links = sum(len(r.links) for r in results)
        print(f"Crawl complete: {total_pages} pages, {total_links} links found")
        if errors:
            print(f"Errors: {errors} pages failed")

    return 0


def main() -> None:
    """Synchronous entry point."""
    try:
        sys.exit(asyncio.run(run()))
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
