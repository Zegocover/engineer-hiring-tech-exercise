import argparse
import asyncio

from ._crawler import Crawler
from .schemas import PageReport, SiteReport


async def main(base_url: str) -> SiteReport:
    return await Crawler().crawl(base_url)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a URL.")
    parser.add_argument("url", type=str, help="The URL to process.")
    args = parser.parse_args()

    report = asyncio.run(main(args.url))

    for page in report.pages:
        print(f"{page.status} {page.url}")
        if not page.links:
            print(" * No links *")
            continue

        for link in page.links:
            print(f" - {link}")
