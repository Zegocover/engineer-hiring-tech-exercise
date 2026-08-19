import argparse
import asyncio
import logging
from urllib.parse import urlsplit

from site_crawler.parser import extract_links_from_url

logger = logging.getLogger(__name__)


async def crawl_pages(
    base_url: str, depth_limit: int | None
) -> None:
    async def fetch_page(url: str) -> tuple[str, list[str]]:
        links = await asyncio.to_thread(extract_links_from_url, url)
        return url, links

    pending = {base_url}
    visited: set[str] = set()
    current_depth = 0

    while pending and (
        depth_limit is None or current_depth <= depth_limit
    ):
        urls = pending - visited
        visited.update(urls)
        next_pending: set[str] = set()

        tasks = [fetch_page(url) for url in urls]
        for task in asyncio.as_completed(tasks):
            url, links = await task
            print(url)
            print(*links, sep="\n")
            next_pending.update(links)

        pending = next_pending
        current_depth += 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="site-crawler",
        description="Crawl pages belonging to one exact domain.",
    )
    parser.add_argument(
        "base_url", help="HTTP(S) URL at which to start crawling"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=None,
        help=(
            "Maximum number of levels to crawl from the base URL. "
            "Defaults to unlimited depth."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    domain = urlsplit(args.base_url).hostname or args.base_url
    depth_limit = (
        f"{args.depth} depth limit"
        if args.depth is not None
        else "unlimited depth limit"
    )
    logger.info("Starting crawl of %s (%s)", domain, depth_limit)
    asyncio.run(crawl_pages(args.base_url, args.depth))
    return 0
