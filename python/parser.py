import asyncio
import pprint
from collections import defaultdict
from utils.html_parser import parse_urls_from_html
from utils.urls import within_subdomain, is_relative_url

from clients.client import get_html

class Parser:

    def __init__(self, url):
        self.base_url = url
        self.processed = set()
        self.to_process = asyncio.Queue()
        self.process_copy = set()
        self.loop = asyncio.get_event_loop()
        self.output = defaultdict(list)
        self.tasks = []

    async def process(self):
        await self.to_process.put(self.base_url)
        self.process_copy.add(self.base_url)
        for i in range(3):
            self.tasks.append(asyncio.create_task(self._worker(i)))
        await self.to_process.join()
        pprint.pprint(self.output)
        for task in self.tasks:
            task.cancel()


    async def _worker(self, i):
        while True:
            url = await self.to_process.get()
            self.processed.add(url)
            links = await self._get_links(url)
            self._add_to_output(url ,[link for link in links if link])
            links = [f"{self.base_url}{link}" if is_relative_url(link) else link for link in links]
            domain_match_links = [url for url in links if within_subdomain(url, self.base_url)]
            await self.add_urls_to_be_processed(domain_match_links)
            self.to_process.task_done()


    async def add_urls_to_be_processed(self, links):
        for link in links:
            not_processed = link not in self.processed
            not_in_queue = link not in self.process_copy
            if not_processed and not_in_queue:
                self.process_copy.add(link)
                await self.to_process.put(link)

    def _add_to_output(self, url, links):
        self.output[url] = links


    async def _get_links(self,url):
        links = []
        try:
            html = await get_html(url)
            links = parse_urls_from_html(html)
        except Exception as err:
            print(f"Error fetching {url}. Status code: , response: {err}")
        return links
