from asyncio import Queue, QueueShutDown, create_task

from ._fetcher import Fetcher
from ._parser import Parser
from .schemas import FetchResult, PageReport, SiteReport


class Crawler:
    def __init__(self: "Crawler", parser=None, fetcher=None):
        self._fetcher = fetcher
        self._parser = parser

        if not self._fetcher:
            self._fetcher = Fetcher()

        if not self._parser:
            self._parser = Parser()

        self._parser_queue = Queue()
        self._fetcher_queue = Queue()

    async def _fetcher_worker(self: "Crawler"):
        while True:
            try:
                url: str = await self._fetcher_queue.get()
            except QueueShutDown:
                break
            else:
                fetch_result: FetchResult = await self._fetcher.fetch(url)
                await self._parser_queue.put(fetch_result)
                self._fetcher_queue.task_done()

    def _site_crawled(self: "Crawler") -> bool:
        return self._fetcher_queue.empty() and self._parser_queue.empty()

    async def _parser_worker(self: "Crawler"):
        page_reports: list[PageReport] = list()
        visited_urls: set = set()

        while True:
            fetch_result: FetchResult = await self._parser_queue.get()
            visited_urls.add(fetch_result.url)

            parsed_urls: set = self._parser.parse(fetch_result.url, fetch_result.text)

            unvisited_urls = parsed_urls.difference(visited_urls)

            for url in unvisited_urls:
                await self._fetcher_queue.put(url)

            page_reports.append(
                PageReport(
                    url=fetch_result.url,
                    status=fetch_result.status,
                    links=parsed_urls,
                )
            )

            self._parser_queue.task_done()

            await self._fetcher_queue.join()
            if self._site_crawled():
                self._fetcher_queue.shutdown()
                break

        return SiteReport(pages=page_reports)

    async def crawl(self: "Crawler", base_url: str, fetchers: int = 5) -> SiteReport:
        await self._fetcher_queue.put(base_url)
        parser_task = create_task(self._parser_worker(), name="parser")

        for index in range(fetchers):
            create_task(self._fetcher_worker(), name=f"fetcher {index}")

        return await parser_task
