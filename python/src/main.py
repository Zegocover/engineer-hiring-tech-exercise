"""
Main Entry Point
----------------

CLI interface for the Web Crawler.
Parses arguments (URL, concurrency, output file, rate limit) and starts the async crawler.
"""
import argparse
import asyncio
import sys
from .crawler import Crawler

def validate_args(args):
    """Validates command line arguments."""
    if not args.url.startswith(('http://', 'https://')):
        print("Error: URL must start with http:// or https://")
        sys.exit(1)
        
    if args.concurrency <= 0:
        print("Error: Concurrency must be a positive integer")
        sys.exit(1)
        
    if args.rate_limit <= 0:
        print("Error: Rate limit must be a positive float")
        sys.exit(1)

async def async_main(args):
    crawler = Crawler(args.url, concurrency=args.concurrency, output_file=args.output, rate_limit=args.rate_limit)
    await crawler.crawl()

def main():
    parser = argparse.ArgumentParser(description="Python Async Web Crawler")
    parser.add_argument("url", help="The base URL to start crawling from")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent requests (default: 10)")
    parser.add_argument("--rate-limit", type=float, default=5, help="Maximum requests per second (default: 0)")
    parser.add_argument("--output", type=str, default="results.csv", help="Output CSV file for results (default: results.csv)")
    
    args = parser.parse_args()
    
    validate_args(args)
    
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("\nCrawler stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
