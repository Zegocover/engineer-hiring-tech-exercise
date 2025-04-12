from crawlspace import Crawler
from crawlspace.schemas import PageReport, SiteReport


async def test_crawler():
    crawler = Crawler()
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
