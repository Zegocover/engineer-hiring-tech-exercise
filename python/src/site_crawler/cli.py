import argparse
import asyncio
import logging
from urllib.parse import urlsplit

import httpx

from site_crawler.parser import extract_links_from_url

logger = logging.getLogger(__name__)


def validate_base_url(value: str) -> str:
    if any(character.isspace() for character in value):
        raise argparse.ArgumentTypeError(
            "base_url must not contain whitespace"
        )

    normalized_value = (
        value if "://" in value else f"https://{value}"
    )

    try:
        parsed = urlsplit(normalized_value)
        hostname = parsed.hostname
        parsed.port
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"invalid base_url: {error}"
        ) from error

    if parsed.scheme not in {"http", "https"} or hostname is None:
        raise argparse.ArgumentTypeError(
            "base_url must be a valid HTTP(S) URL with a hostname"
        )

    return normalized_value


async def crawl_pages(
    base_url: str, depth_limit: int | None, include_duplicates: bool
) -> None:
    async def fetch_page(
        url: str,
    ) -> tuple[str, list[str] | None, Exception | None]:
        try:
            links = await asyncio.to_thread(
                extract_links_from_url, url, include_duplicates
            )
        except (httpx.HTTPError, httpx.RequestError) as error:
            return url, None, error
        return url, links, None

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
            url, links, error = await task
            if error is not None:
                status = (
                    error.response.status_code
                    if hasattr(error, "response")
                    else error
                )
                print(f"Error fetching {url}: {status}")
                continue

            assert links is not None
            print(f"URL: {url} contains {len(links)} links:")
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
        "base_url",
        type=validate_base_url,
        help="HTTP(S) URL at which to start crawling",
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
    parser.add_argument(
        "--include-duplicates",
        action="store_true",
        help="Include repeated links found on the same page.",
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
    asyncio.run(
        crawl_pages(args.base_url, args.depth, args.include_duplicates)
    )
    return 0
