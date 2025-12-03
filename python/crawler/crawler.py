import logging
from collections import defaultdict
from typing import List, Optional, Dict
from urllib.parse import urlparse, urljoin, urldefrag

from aiohttp import ClientSession
from bs4 import BeautifulSoup

from .util import validate_url
from .traverse import PooledTraverse, BFSTraverse


logger = logging.getLogger(__name__)


TIMEOUT = 10
ACCEPTED_CONTENT_TYPES = {
    'text/html',
    'text/xhtml',
    'application/xhtml+xml',
    'application/xhtml',
    'application/html',
}


class PooledCrawler:
    def __init__(self, url: str, workers: int, session: ClientSession) -> None:
        if not validate_url(url):
            raise ValueError(f"Invalid URL: {url}")
        self._url = url.rstrip("/")
        self._domain = urlparse(url).netloc
        self._workers = workers
        self._session: ClientSession = session
        self._sitemap = defaultdict(list)

    async def run(self) -> Dict[str, List[str]]:
        traverse = PooledTraverse(self._url, self.crawl, self._workers)
        await traverse.run()
        return self._sitemap

    async def crawl(self, url: str) -> List[str]:
        logging.debug(f"Crawling {url}")
        links = []

        html = await self.fetch(url)
        if html is not None:
            links = self.extract_links(html)
            for link in links:
                self._sitemap[url].append(link)

        return links

    async def fetch(self, url: str) -> Optional[str]:
        logging.debug(f"Fetching {url}")
        try:
            async with self._session.get(url, timeout=TIMEOUT) as response:
                content_type = response.headers.get("Content-Type", "")
                if all(a not in content_type for a in ACCEPTED_CONTENT_TYPES):
                    logging.debug(f"{url} had unaccepted content type {content_type}")
                    return None

                return await response.text(errors="ignore")
        except Exception as e:
            logging.warning(f"Failed to fetch {url}: {e}")
            return None

    def extract_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links = set()

        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()

            if href and not href.startswith("#") and not href.startswith(("mailto:", "tel:", "javascript:")):
                parsed = urlparse(urljoin(self._url + "/", href))

                if parsed.netloc == self._domain:
                    links.add(urldefrag(parsed.geturl())[0].rstrip("/"))

        return list(links)

