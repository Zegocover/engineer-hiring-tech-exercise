import argparse
import asyncio
from asyncio.log import logger

from site_crawler.crawler import Crawler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Asynchronous web crawler")
    parser.add_argument("base_url", type=str, help="The base URL to start crawling from")
    parser.add_argument("-d", "--max-depth", type=int, default=1,
                        help="Max crawl depth (0 = only base URL). Default: 1")
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    crawler = Crawler()

    async def _main() -> None:
        try:
            async for links in crawler.crawl(args.base_url, max_depth=args.max_depth):
                for l in sorted(links):
                    print(l)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")

    asyncio.run(_main())

if __name__ == "__main__":
    main()