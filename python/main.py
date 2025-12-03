import argparse
import asyncio
from asyncio.log import logger

from site_crawler.crawler import Crawler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Asynchronous web crawler")
    parser.add_argument("base_url", type=str, help="The base URL to start crawling from")
    parser.add_argument(
        "-c",
        "--concurrency",
        type=int,
        default=10,
        help="Number of concurrent requests (default: 10)",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "-m",
        "--max-pages",
        type=int,
        default=100,
        help="Maximum number of pages to crawl (default: 100)",
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    crawler = Crawler(args.base_url, concurrency=args.concurrency, timeout=args.timeout, max_pages=args.max_pages)

    async def _main() -> None:
        try:
            async for links in crawler.crawl():
                for l in sorted(links):
                    print(l)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")

    asyncio.run(_main())

if __name__ == "__main__":
    main()