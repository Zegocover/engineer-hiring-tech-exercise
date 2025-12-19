import argparse
from crawler.crawler import Crawler


def main():
    parser = argparse.ArgumentParser(description="Zego Web Crawler")
    parser.add_argument("url", help="Starting URL to crawl")
    parser.add_argument(
        "--max-pages", type=int, default=500, help="Maximum pages to crawl"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of concurrent requests",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests (seconds)",
    )

    args = parser.parse_args()

    crawler = Crawler(
        start_url=args.url,
        max_pages=args.max_pages,
        concurrency=args.concurrency,
        delay=args.delay,
    )
    crawler.crawl()
