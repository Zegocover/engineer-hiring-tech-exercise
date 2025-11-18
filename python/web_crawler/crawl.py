import logging

from web_crawler.mt_webcrawler import MTWebCrawler
from web_crawler.url import URL
from web_crawler.webcrawler import WebCrawler

def main(url: str, max_depth: int, multi_threaded: bool | None) -> None:
    if multi_threaded:
        logging.warning("Multi-threaded crawling will not terminate")
        wc = MTWebCrawler(max_depth=max_depth)

    else:
        wc = WebCrawler(max_depth=max_depth)

    wc.crawl(URL(url))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        type=str,
        help="Starting URL to crawl",
        default="https://www.barrierreef.org/the-reef/animals/manta-ray"
    )
    parser.add_argument(
        "--depth",
        type=int,
        help="Maximum depth to crawl",
        default=2
    )
    parser.add_argument(
        "--multi-threaded",
        action=argparse.BooleanOptionalAction
    )
    args = parser.parse_args()

    main(args.url, args.depth, args.multi_threaded)
