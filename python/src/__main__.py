import argparse
import logging
import multiprocessing
import signal
from urlcrawler import UrlCrawler, HttpDownloader, HtmlParser

if __name__ == "__main__":
    cpu_count = multiprocessing.cpu_count()

    parser = argparse.ArgumentParser(description="URL Crawler")
    parser.add_argument("url", type=str, help="The URL to process.")
    parser.add_argument(
        "--threads",
        type=int,
        default=cpu_count,
        help="Number of threads to use (defaults to cpu_count).",
    )
    parser.add_argument(
        "--cache",
        action="store_true",
        help="Enable using of local cache",
    )
    parser.add_argument(
        "--log",
        default="INFO",
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=args.log.upper())
    downloader = HttpDownloader(args.cache)
    parser = HtmlParser()
    crawler = UrlCrawler(args.url, args.threads, downloader, parser)
    # Enables Ctrl+C exit signal from CMD
    signal.signal(signal.SIGINT, lambda _sig, _frame: crawler.stop())
    crawler.start()
