"""
CLI entry point for the web crawler.
"""
import argparse
import asyncio
import sys

from .crawler import WebCrawler

def main():
    parser = argparse.ArgumentParser(description="A simple web crawler.")
    parser.add_argument("url", help="The starting URL to crawl.")
    parser.add_argument("-c", "--concurrent", type=int, default=5,
                        help="Maximum number of concurrent requests (default: 5).")
    args = parser.parse_args()

    start_url = args.url
    max_concurrent_requests = args.concurrent

    # Basic URL validation
    if not start_url.startswith(("http://", "https://")):
        print("Error: URL must start with 'http://' or 'https://'")
        sys.exit(1)

    crawler = WebCrawler(start_url, max_concurrent_requests)
    asyncio.run(crawler.start())

if __name__ == "__main__":
    main()