import asyncio
from typing import Dict

import pytest

from site_crawler.crawler import Crawler


class FakeFetcher:
    def __init__(self, mapping: Dict[str, str]):
        self.mapping = mapping

    async def fetch(self, session, url: str):
        # return mapping if present, else None to simulate missing page
        return self.mapping.get(url)


@pytest.mark.parametrize(
    "max_depth,expected",
    [
        (0, {"https://example.com/"}),
        (1, {"https://example.com/", "https://example.com/about", "https://example.com/blog/post1"}),
        (
            2,
            {
                "https://example.com/",
                "https://example.com/about",
                "https://example.com/blog/post1",
                "https://example.com/contact",
                "https://example.com/blog/post2",
            },
        ),
    ],
)
def test_crawl_depth_and_hostname_filtering(max_depth: int, expected: set[str]):
    base = "https://example.com/"
    mapping = {
        base: (
            '<a href="/about">About</a>'
            '<a href="https://sub.example.com/page">Sub</a>'
            '<a href="/blog/post1">Post1</a>'
        ),
        "https://example.com/about": '<a href="/contact">Contact</a>',
        "https://example.com/blog/post1": '<a href="/blog/post2">Post2</a>',
        "https://example.com/blog/post2": '<a href="/blog/post3">Post3</a>',
        # subdomain pages are present but should be filtered by is_valid
        "https://sub.example.com/page": '<a href="/should-not-be-included">x</a>',
    }

    fetcher = FakeFetcher(mapping)
    crawler = Crawler(fetcher=fetcher)

    async def _run():
        async for links in crawler.crawl(base, max_depth=max_depth):
            return links

    got = asyncio.run(_run())
    assert got == expected
