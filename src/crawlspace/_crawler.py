from .schemas import PageReport, SiteReport


class Crawler:
    async def crawl(self: "Crawler", base_url: str) -> SiteReport:
        return SiteReport(
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
