import argparse
import asyncio
from urllib.parse import urlparse
import sys
from .src.web_crawler import WebCrawler

def main():
    p = argparse.ArgumentParser(prog="python -m web_crawler")
    p.add_argument("base_url")
    p.add_argument("--concurrency", "-c", type=int, default=10)
    p.add_argument("--max-pages", type=int, default=100)
    p.add_argument("--max-depth", type=int, default=None)
    p.add_argument("--timeout", type=int, default=10)
    p.add_argument("--user-agent", type=str, default="web-crawler-exercise/1.0")
    p.add_argument("--ignore-robots-txt", action="store_true")
    p.add_argument("--ignore-crawl-delay", action="store_true")
    p.add_argument("--no-strip-tracking-params", action="store_true")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

     # Basic CLI validation for base_url to fail fast.
    parsed = urlparse(args.base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        print(f"Error: input must be an absolute http(s) URL with a host: {args.base_url!r}", file=sys.stderr)
        sys.exit(2)

    try:
        crawler = WebCrawler(
            args.base_url,
            concurrency=args.concurrency,
            max_pages=args.max_pages,
            max_depth=args.max_depth,
            user_agent=args.user_agent,
            ignore_robots=args.ignore_robots_txt,
            ignore_crawl_delay=args.ignore_crawl_delay,
            strip_tracking_params=not args.no_strip_tracking_params,
            timeout=args.timeout,
            verbose=args.verbose,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error creating WebCrawler: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        asyncio.run(crawler.crawl())
    except Exception as e:
        print(f"Error during crawl: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
