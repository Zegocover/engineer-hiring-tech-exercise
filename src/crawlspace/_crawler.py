from asyncio import Queue, QueueShutDown, create_task

from .schemas import FetchResult, PageReport, SiteReport


class Crawler:
    def __init__(self: "Crawler", parser=None):
        if not parser:
            raise Exception("A parser is required")

        self._parser = parser
        self._parser_queue = Queue()

    async def _parser_worker(self: "Crawler"):
        page_reports: list[PageReport] = list()

        while True:
            try:
                fetch_result: FetchResult = await self._parser_queue.get()
            except QueueShutDown:
                break
            else:
                parsed_links = self._parser.parse(fetch_result.url, fetch_result.text)
                page_reports.append(
                    PageReport(
                        url=fetch_result.url,
                        status=fetch_result.status,
                        links=parsed_links,
                    )
                )
                self._parser_queue.task_done()

        return SiteReport(pages=page_reports)

    async def crawl(self: "Crawler", base_url: str) -> SiteReport:
        parser_task = create_task(self._parser_worker())

        fetch_results = [
            FetchResult(url="http://localhost:8888", status=200, text=""),
            FetchResult(url="http://localhost:8888/empty-page", status=200, text=""),
        ]

        for fetch_result in fetch_results:
            await self._parser_queue.put(fetch_result)

        self._parser_queue.shutdown()

        return await parser_task
