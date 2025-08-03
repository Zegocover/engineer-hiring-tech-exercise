import argparse
import logging
import multiprocessing
from urlcrawler import URLCrawler, HttpDownloader, HtmlParser

_LOG = logging.getLogger(__name__)

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
        "--use-cache",
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
    downloader = HttpDownloader(args.use_cache)
    parser = HtmlParser()
    crawler = URLCrawler(args.url, args.threads, downloader, parser)
    crawler.start()
