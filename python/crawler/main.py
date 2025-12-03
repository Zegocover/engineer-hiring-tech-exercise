import enum
import click
import asyncio
import logging
from aiohttp import ClientSession

from .util import validate_url
from .crawler import PooledCrawler


class LogLevel(enum.Enum):
    CRITICAL = logging.CRITICAL
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    INFO = logging.INFO
    DEBUG = logging.DEBUG


async def run(url: str, workers: int,) -> None:
    async with ClientSession() as session:
        crawler = PooledCrawler(url, workers, session)
        sitemap = await crawler.run()
        for url, urls in sitemap.items():
            print(url)
            for url in urls:
                print("  " + url)


@click.command()
@click.option('--url', type=str, help="URL to crawl.")
@click.option('--workers', type=int, default=10, help='Number of workers to use.')
@click.option("--log-level", type=click.Choice(LogLevel, case_sensitive=False), default="WARNING", help="Set log level.")
def main(url: str, workers: int, log_level: LogLevel) -> None:
    logging.basicConfig(level=log_level.value)

    if not validate_url(url):
        raise ValueError(f"Invalid URL: {url}")

    asyncio.run(run(url, workers))


if __name__ == "__main__":
    main()
