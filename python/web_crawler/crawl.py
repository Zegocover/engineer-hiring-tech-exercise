import logging

from web_crawler.mt_webcrawler import MTWebCrawler
from web_crawler.st_webcrawler import STWebCrawler
from web_crawler.url import URL

logger = logging.getLogger(__name__)

def main(url: str, max_depth: int, multi_threaded: bool | None) -> None:
    logging.basicConfig(level=logging.INFO)

    if multi_threaded:
        logger.info("Multi-threaded crawling")
        logger.warning("Multi-threaded crawling will not terminate")
        wc = MTWebCrawler(max_depth=max_depth)

    else:
        logger.info("Single-threaded crawling")
        wc = STWebCrawler(max_depth=max_depth)

    wc.crawl(URL(url))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        type=str,
        help="Starting URL to crawl",
        default="https://www.barrierreef.org/the-reef/animals/manta-ray",
    )
    parser.add_argument("--depth", type=int, help="Maximum depth to crawl", default=1)
    parser.add_argument("--multi-threaded", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    main(args.url, args.depth, args.multi_threaded)
