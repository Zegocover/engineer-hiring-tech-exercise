"""Single-domain async web crawler.

Usage: python crawler.py https://example.com

For every page found on the base URL's domain, prints the page URL followed
by every URL discovered on that page. Only URLs on the exact same host are
crawled further — other domains and subdomains are printed but never visited.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
import sys
import urllib.robotparser
from urllib.parse import urldefrag, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger("crawler")

USER_AGENT = "ZegoExerciseCrawler/1.0 (tech exercise; contact: zaid@dataakkadian.com)"
RETRY_STATUSES = {429, 500, 502, 503, 504}
CAPTCHA_MARKERS = ("captcha", "cf-challenge", "are you a human", "attention required")


class FetchError(Exception):
    """A URL could not be fetched and should be skipped, not crashed on."""


class Fetcher:
    """Fetches pages with timeouts, bounded retries and exponential backoff.

    Retries network errors, 429 and 5xx with jittered exponential backoff,
    honouring Retry-After when the server sends one. Captcha/anti-bot walls
    are detected and given up on immediately — retrying a captcha only gets
    the crawler (and the site) hurt.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 30.0,
        sleep=asyncio.sleep,
    ):
        self._client = client
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._sleep = sleep

    async def fetch(self, url: str) -> httpx.Response:
        last_error = "unknown error"
        for attempt in range(self._max_retries + 1):
            retry_after = None
            try:
                response = await self._client.get(url)
            except httpx.HTTPError as exc:
                last_error = f"network error: {exc}"
            else:
                if response.status_code < 400:
                    return response
                if self._looks_like_captcha(response):
                    raise FetchError(f"{url} is behind a captcha/anti-bot wall, giving up")
                if response.status_code not in RETRY_STATUSES:
                    raise FetchError(f"{url} returned HTTP {response.status_code}")
                last_error = f"HTTP {response.status_code}"
                retry_after = response.headers.get("retry-after")
            if attempt < self._max_retries:
                await self._sleep(self._delay(attempt, retry_after))
        raise FetchError(f"{url} failed after {self._max_retries + 1} attempts ({last_error})")

    def _delay(self, attempt: int, retry_after: str | None) -> float:
        delay = min(self._max_delay, self._base_delay * 2**attempt)
        delay += random.uniform(0, self._base_delay)  # jitter: don't retry in lockstep
        if retry_after and retry_after.isdigit():
            delay = max(delay, float(retry_after))
        return delay

    @staticmethod
    def _looks_like_captcha(response: httpx.Response) -> bool:
        if response.status_code not in (403, 503):
            return False
        body = response.text[:2048].lower()
        return any(marker in body for marker in CAPTCHA_MARKERS)


def extract_links(html: str, page_url: str) -> list[str]:
    """All unique http(s) URLs linked from a page, absolute, fragments stripped."""
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        url = urldefrag(urljoin(page_url, anchor["href"])).url
        if urlparse(url).scheme in ("http", "https") and url not in seen:
            seen.add(url)
            links.append(url)
    return links


class Crawler:
    """Breadth-ish concurrent crawl of a single host.

    A shared queue feeds N worker tasks; a `seen` set deduplicates before
    enqueue so every discovered URL is enqueued at most once. `max_pages` bounds both
    memory and how much load we put on the site.
    """

    def __init__(
        self,
        base_url: str,
        fetcher: Fetcher,
        *,
        concurrency: int = 10,
        max_pages: int = 1000,
        robots: urllib.robotparser.RobotFileParser | None = None,
        out=print,
    ):
        self._base_url = urldefrag(base_url).url
        self._netloc = urlparse(self._base_url).netloc
        self._fetcher = fetcher
        self._concurrency = concurrency
        self._max_pages = max_pages
        self._robots = robots
        self._out = out
        self._seen: set[str] = set()

    def in_scope(self, url: str) -> bool:
        parsed = urlparse(url)
        # exact host match: other domains AND subdomains are out of scope
        return parsed.scheme in ("http", "https") and parsed.netloc == self._netloc

    async def crawl(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._enqueue(self._base_url, queue)
        workers = [asyncio.create_task(self._worker(queue)) for _ in range(self._concurrency)]
        await queue.join()
        for worker in workers:
            worker.cancel()

    def _enqueue(self, url: str, queue: asyncio.Queue[str]) -> None:
        if url not in self._seen and len(self._seen) < self._max_pages:
            self._seen.add(url)
            queue.put_nowait(url)

    async def _worker(self, queue: asyncio.Queue[str]) -> None:
        while True:
            url = await queue.get()
            try:
                await self._process(url, queue)
            except FetchError as exc:
                log.warning("%s", exc)
            except Exception:
                log.exception("unexpected error processing %s", url)
            finally:
                queue.task_done()

    async def _process(self, url: str, queue: asyncio.Queue[str]) -> None:
        if self._robots and not self._robots.can_fetch(USER_AGENT, url):
            log.info("robots.txt disallows %s, skipping", url)
            return
        response = await self._fetcher.fetch(url)
        final_url = str(response.url)
        if not self.in_scope(final_url):
            if url == self._base_url:
                # apex -> www and friends: otherwise the crawl is silently empty
                log.error(
                    "base URL %s redirects off-host to %s — nothing in scope; re-run with that URL",
                    url,
                    final_url,
                )
            else:
                log.info("%s redirected off-domain to %s, skipping", url, final_url)
            return
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            log.info("%s is not HTML (%s), skipping", url, content_type or "unknown type")
            return
        links = extract_links(response.text, final_url)
        # one print per page so concurrent workers never interleave output
        self._out("\n".join([url, *(f"  {link}" for link in links)]))
        for link in links:
            if self.in_scope(link):
                self._enqueue(link, queue)


async def load_robots(
    client: httpx.AsyncClient, base_url: str
) -> urllib.robotparser.RobotFileParser:
    parser = urllib.robotparser.RobotFileParser()
    try:
        response = await client.get(urljoin(base_url, "/robots.txt"))
        if response.status_code in (401, 403):
            # a locked-down robots.txt means we're not welcome (stdlib read() semantics)
            parser.disallow_all = True
        else:
            parser.parse(response.text.splitlines() if response.status_code == 200 else [])
    except httpx.HTTPError:
        parser.parse([])  # unreachable robots.txt -> allow everything
    return parser


async def run(base_url: str, concurrency: int, max_pages: int, respect_robots: bool = True) -> None:
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(10.0),
        limits=httpx.Limits(max_connections=concurrency),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        robots = await load_robots(client, base_url) if respect_robots else None
        crawler = Crawler(
            base_url,
            Fetcher(client),
            concurrency=concurrency,
            max_pages=max_pages,
            robots=robots,
        )
        await crawler.crawl()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Crawl a single domain and print every page's links."
    )
    parser.add_argument("url", help="base URL to crawl, e.g. https://example.com")
    parser.add_argument(
        "--concurrency", type=int, default=10, help="parallel requests (default 10)"
    )
    parser.add_argument(
        "--max-pages", type=int, default=1000, help="stop after this many pages (default 1000)"
    )
    parser.add_argument(
        "--no-robots", action="store_true", help="ignore robots.txt (be nice: don't)"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="log skipped and failed URLs")
    args = parser.parse_args(argv)

    parsed = urlparse(args.url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        parser.error(f"'{args.url}' is not an absolute http(s) URL")
    if args.concurrency < 1 or args.max_pages < 1:
        parser.error("--concurrency and --max-pages must be >= 1")

    logging.basicConfig(level=logging.ERROR, format="%(levelname)s %(message)s")
    if args.verbose:
        log.setLevel(logging.INFO)  # only our logger — keeps httpx's own INFO lines out
    try:
        asyncio.run(
            run(args.url, args.concurrency, args.max_pages, respect_robots=not args.no_robots)
        )
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
