import pytest

from crawlspace import Crawler
from crawlspace.schemas import PageReport, SiteReport


class MockParser:
    @staticmethod
    def parse(url: str, page: str) -> list[str]:
        match url:
            case "http://localhost:8888":
                return ["http://localhost:8888/empty-page"]

            case "http://localhost:8888/empty-page":
                return list()

            case _:
                return list()


async def test_crawler():
    crawler = Crawler(parser=MockParser)
    base_url = "http://localhost:8888"

    result = await crawler.crawl(base_url)

    assert result == SiteReport(
        pages=[
            PageReport(
                url="http://localhost:8888",
                status=200,
                links=["http://localhost:8888/empty-page"],
            ),
            PageReport(
                url="http://localhost:8888/empty-page",
                status=200,
                links=[],
            ),
        ]
    )
