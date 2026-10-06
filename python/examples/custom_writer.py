"""Plugging a custom component into the crawler.

``LinkGraphWriter`` is a plain class: it doesn't import or subclass anything
from ``site_crawler``, it just has ``write`` and ``aclose`` methods, which is
all the :class:`site_crawler.Writer` protocol asks for. Fetchers and parsers
can be swapped the same way.

Run:  uv run python -m examples.custom_writer https://books.toscrape.com/ 20
"""

from __future__ import annotations

import asyncio
import sys
from collections import Counter

from site_crawler import CrawlConfig, Crawler, Fetcher, PageResult


class LinkGraphWriter:
    """Builds an in-memory link graph instead of printing pages."""

    def __init__(self) -> None:
        self.graph: dict[str, tuple[str, ...]] = {}
        self.closed = False

    async def write(self, result: PageResult) -> None:
        self.graph[result.url] = result.links

    async def aclose(self) -> None:
        self.closed = True

    def most_linked(self, n: int = 5) -> list[tuple[str, int]]:
        counts = Counter(link for links in self.graph.values() for link in links)
        return counts.most_common(n)


async def build_graph(
    url: str, max_pages: int = 50, fetcher: Fetcher | None = None
) -> LinkGraphWriter:
    writer = LinkGraphWriter()
    await Crawler(CrawlConfig(url, max_pages=max_pages), fetcher=fetcher, writer=writer).run()
    return writer


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "https://books.toscrape.com/"
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    graph = asyncio.run(build_graph(url, max_pages))
    print(f"{len(graph.graph)} pages crawled; most linked-to URLs:")
    for link, count in graph.most_linked():
        print(f"{count:5d}  {link}")


if __name__ == "__main__":
    main()
