import argparse
import asyncio
import logging
from urllib.parse import urlsplit

import httpx

from site_crawler.parser import extract_links_from_url_async
from site_crawler.url_policy import UrlPolicy

logger = logging.getLogger(__name__)


def validate_base_url(value: str) -> str:
    """
    Validate and normalize a base URL for crawling. Ensures that the URL is a
    valid HTTP(S) URL with a hostname, and normalizes it to include the
    scheme (HTTPS) if missing.
    """
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
    base_url: str,
    depth_limit: int | None,
    include_duplicates: bool,
    concurrency: int = 5,
) -> None:
    """
    Crawl pages starting from the base URL, up to the specified depth limit.
    Fetches pages concurrently, extracts links, and prints them to the console.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def fetch_page(
        url: str,
    ) -> tuple[str, list[str] | None, Exception | None]:
        try:
            async with semaphore:
                links = await extract_links_from_url_async(
                    client, url, include_duplicates, url_policy
                )
        except (httpx.HTTPError, httpx.RequestError) as error:
            return url, None, error
        return url, links, None

    async with httpx.AsyncClient(follow_redirects=False) as client:
        pending = {base_url}
        visited: set[str] = set()
        url_policy = UrlPolicy(base_url)
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
                for link in links:
                    normalized_link = url_policy.normalize(link)
                    if normalized_link is None:
                        # Skipping URL outside crawl domain
                        continue
                    if normalized_link not in visited:
                        next_pending.add(normalized_link)

            pending = next_pending
            current_depth += 1


def positive_int(value: str) -> int:
    """
    Validate that a value is a positive integer.
    """
    int_value = int(value)
    if int_value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return int_value


def build_parser() -> argparse.ArgumentParser:
    """
    Build and return the argument parser for the site crawler CLI.
    """
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
        type=positive_int,
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
    parser.add_argument(
        "--concurrency",
        type=positive_int,
        default=5,
        help="Maximum number of pages to fetch concurrently (default: 5).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    Start the site crawler CLI, parse arguments, and initiate the crawling
    process.
    """
    args = build_parser().parse_args(argv)
    domain = urlsplit(args.base_url).hostname or args.base_url
    depth_limit = (
        f"{args.depth} depth limit"
        if args.depth is not None
        else "unlimited depth limit"
    )
    logger.info("Starting crawl of %s (%s)", domain, depth_limit)
    asyncio.run(
        crawl_pages(
            args.base_url,
            args.depth,
            args.include_duplicates,
            args.concurrency,
        )
    )
    return 0
