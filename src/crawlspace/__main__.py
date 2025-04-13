import argparse
import asyncio
import logging

from ._crawler import Crawler
from .schemas import SiteReport

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("crawlspace.log", "w"),
    ],
)
logger = logging.getLogger(__name__)


async def main(base_url: str) -> SiteReport:
    logger.info(f"Starting crawl at {base_url}")
    return await Crawler().crawl(base_url)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a URL.")
    parser.add_argument("url", type=str, help="The URL to process.")
    args = parser.parse_args()

    report = asyncio.run(main(args.url))

    sorted_pages = sorted(report.pages, key=lambda x: len(x.url))

    for page in sorted_pages:
        print(f"{page.status} {page.url}")
        if not page.links:
            print(" * No links *")
            continue

        sorted_links = sorted(list(page.links))

        for link in sorted_links:
            print(f" - {link}")
