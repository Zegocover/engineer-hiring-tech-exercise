import asyncio
import time
from typing import Optional, Set, List
from urllib.parse import urlparse, urljoin, urlunparse, parse_qsl, urlencode

import aiohttp
from aiohttp import TCPConnector
from bs4 import BeautifulSoup
import re

from .robots import RobotsParser

TRACKING_PARAM_BLACKLIST = [
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "_ga", "_gid", "_gat", "ref", "referrer", "amp"
]


class WebCrawler:
    def __init__(
        self,
        base_url: str,
        concurrency: int = 10,
        max_pages: int = 100,
        max_depth: Optional[int] = None,
        timeout: int = 10,
        user_agent: str = "web-crawler-exercise/1.0",
        ignore_robots: bool = False,
        ignore_crawl_delay: bool = False,
        strip_tracking_params: bool = True,
        tracking_blacklist: Optional[List[str]] = None,
        tracking_whitelist: Optional[List[str]] = None,
        verbose: bool = False,
    ):
        # validate base_url so later logic can assume an http(s) host
        if not isinstance(base_url, str):
            raise ValueError(f"base_url must be a string, got: {type(base_url)!r}")
        parsed_base = urlparse(base_url)
        if parsed_base.scheme not in ("http", "https") or not parsed_base.hostname:
            raise ValueError(f"base_url must be an absolute http(s) URL with a host: {base_url!r}")
        
        self.base_url = base_url.rstrip("/")
        self.base_host = parsed_base.hostname
        # crawling settings
        self.concurrency = concurrency
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout = timeout
        # user-agent and robots.txt settings
        self.user_agent = user_agent
        self.ignore_robots = ignore_robots
        self.ignore_crawl_delay = ignore_crawl_delay
        # URL normalization settings
        self.strip_tracking_params = strip_tracking_params
        self.tracking_blacklist = set(tracking_blacklist or TRACKING_PARAM_BLACKLIST)
        self.tracking_whitelist = set(tracking_whitelist or [])
        # output setting
        self.verbose = verbose

        self.visited: Set[str] = set()
        # asyncio primitives must be created on the running loop; initialize in crawl()
        self.frontier = None
        self.sem = None
        self.robots = None
        self.last_request_time = {}  # per-host timestamps

        # runtime metrics
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.request_count: int = 0
        self.success_count: int = 0
        self.fail_count: int = 0
        self.retry_count: int = 0
        self.bytes_fetched: int = 0
        self.total_request_duration: float = 0.0

    async def crawl(self):
        # create asyncio primitives on the active event loop
        self.frontier = asyncio.Queue()
        self.sem = asyncio.Semaphore(self.concurrency)

        # mark start time for metrics
        self.start_time = time.time()
        await self.frontier.put((self.base_url, 0))

        # create a tuned connector to improve throughput (connection pooling + DNS cache)
        connector_limit = max(100, self.concurrency * 2)
        connector_limit_per_host = max(10, self.concurrency)
        connector = TCPConnector(limit=connector_limit, limit_per_host=connector_limit_per_host, ttl_dns_cache=300)

        # reuse a single ClientSession (with the tuned connector) for robots fetch and worker requests
        async with aiohttp.ClientSession(headers={"User-Agent": self.user_agent}, connector=connector) as session:
            self.robots = None
            if not self.ignore_robots:
                self.robots = await self._fetch_robots(session)

            workers = [asyncio.create_task(self._worker(session)) for _ in range(self.concurrency)]
            await self.frontier.join()
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

        # record end time and optionally print summary
        self.end_time = time.time()
        if self.verbose:
            self._print_crawl_summary()
    

    async def _fetch_robots(self, session):
        """Fetch and parse robots.txt using the provided `session`.

        This ensures the same TCPConnector and DNS cache are reused
        for both robots and page fetches.
        """
        try:
            return await RobotsParser.fetch(session, self.base_url)
        except Exception:
            return None

    async def _worker(self, session):
        while True:
            try:
                url, depth = await self.frontier.get()
            except asyncio.CancelledError:
                return
            
            try:
                norm = self._normalise(url)
                # skip urls that failed normalization or are not http(s)
                if not norm:
                    continue
                if norm in self.visited:
                    continue
                if self._should_stop_adding():
                    # stop scheduling new work
                    continue
                if self.robots and not self.ignore_robots and not self.robots.is_allowed(norm, self.user_agent):
                    if self.verbose:
                        print(f"SKIP (robots): {norm}")
                    continue
                await self.sem.acquire()
                try:
                    await self._fetch_and_extract(session, norm, depth)
                finally:
                    self.sem.release()
            finally:
                self.frontier.task_done()

    async def _fetch_and_extract(self, session, url, depth):
        await self._enforce_crawl_delay(url)

        # fetch with retries
        retries = 2
        for attempt in range(retries + 1):
            try:
                # count this request attempt
                self.request_count += 1
                start = time.time()
                async with session.get(url, timeout=self.timeout) as resp:
                    text = await resp.text(errors="ignore")
                    duration = time.time() - start
                    
                    if resp.status == 200:
                        self.visited.add(url)
                        links = self._extract_links(url, text)

                        # metrics for successful request
                        self.success_count += 1
                        self.bytes_fetched += len(text or "")
                        self.total_request_duration += duration

                        # print page and links (human-readable)
                        print(f"Visited: {url}", end=" ")
                        if self.verbose:
                            print(f"({duration:.2f}s)", end="")
                        print("")
                        if links:
                            print("Links:")
                            for l in links:
                                print(f" - {l}")
                        else:
                            print("Links: (none)")

                        # handle canonical
                        canonical = self._extract_canonical(text, url)
                        if canonical:
                            canonical = self._normalise(canonical)
                            if canonical != url and canonical not in self.visited:
                                # prefer canonical url for scheduling
                                await self._maybe_schedule(canonical, depth + 0)

                        # schedule found links
                        if self.max_depth is None or depth + 1 <= self.max_depth:
                            for l in links:
                                await self._maybe_schedule(l, depth + 1)
                                
                    else:
                        # treat 5xx as transient server errors and retry
                        if 500 <= resp.status < 600 and attempt < retries:
                            # exponential backoff before next attempt
                            self.retry_count += 1
                            await asyncio.sleep(0.5 * (2 ** attempt))
                            if self.verbose:
                                print(f"Retry {attempt+1} for {url} due to HTTP {resp.status}")
                            continue
                        # non-200 (or exhausted retries) - treat as visited for counting but don't parse
                        self.visited.add(url)
                        self.fail_count += 1
                    
                    # record last request time if we can determine a host
                    parsed = urlparse(url)
                    host = parsed.hostname
                    if host:
                        self.last_request_time[host] = time.time()
                break
            except Exception as e:
                if attempt < retries:
                    self.retry_count += 1
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    if self.verbose:
                        print(f"Retry {attempt+1} for {url} due to {e}")
                    continue
                else:
                    if self.verbose:
                        print(f"Failed to fetch {url}: {e}")
                    self.visited.add(url)
                    self.fail_count += 1
                    break

    async def _enforce_crawl_delay(self, url):
        if self.robots and not self.ignore_crawl_delay and not self.ignore_robots:
            delay = self.robots.get_crawl_delay(self.user_agent)
            if delay:
                parsed = urlparse(url)
                host = parsed.hostname
                if host:
                    last = self.last_request_time.get(host, 0)
                    wait = delay - (time.time() - last)
                    if wait > 0:
                        if self.verbose:
                            print(f"[DELAY] waiting {wait:.2f}s for {host}")
                        await asyncio.sleep(wait)

    async def _maybe_schedule(self, url: str, depth: int):
        if self._is_same_host(url) and url not in self.visited:
            if self.max_depth is not None and depth > self.max_depth:
                return
            if self._should_stop_adding():
                return
            await self.frontier.put((url, depth))

    def _should_stop_adding(self) -> bool:
        return len(self.visited) >= self.max_pages

    def _is_same_host(self, url: Optional[str]) -> bool:
        if not url:
            return False
        try:
            p = urlparse(url)
        except Exception:
            return False
        return p.hostname == self.base_host

    def _normalise(self, url: str) -> Optional[str]:
        # resolve relative and return None for malformed/non-http(s) URLs
        try:
            url = urljoin(self.base_url + "/", url)
        except Exception:
            if self.verbose:
                print(f"SKIP (normalize error): {url!r}")
            return None
        try:
            p = urlparse(url)
        except Exception:
            if self.verbose:
                print(f"SKIP (unparseable URL): {url!r}")
            return None
        
        scheme = (p.scheme or "").lower()
        if scheme not in ("http", "https"):
            return None

        # parse and strip tracking params
        query = p.query
        if self.strip_tracking_params:
            qs = parse_qsl(query, keep_blank_values=True)
            kept = []
            for k, v in qs:
                if k in self.tracking_whitelist:
                    kept.append((k, v))
                elif k in self.tracking_blacklist:
                    continue
                elif k.startswith("utm_") and "utm_" not in self.tracking_whitelist:
                    continue
                else:
                    kept.append((k, v))
            # remove empty params
            kept = [(k, v) for (k, v) in kept if v != ""]
            query = urlencode(sorted(kept))
        else:
            # keep as-is but remove blank values
            qs = parse_qsl(query, keep_blank_values=True)
            qs = [(k, v) for (k, v) in qs if v != ""]
            query = urlencode(sorted(qs))

        netloc = (p.netloc or "").lower()
        path = p.path or "/"
        new = urlunparse((scheme, netloc, path, "", query, ""))
        return new

    def _extract_links(self, base: str, html: str) -> List[str]:
        # choose XML parser for XML-like payloads to avoid XMLParsedAsHTMLWarning
        parser = "lxml-xml" if re.match(r"^\s*<(\?xml|rss|feed|rdf|xml)\b", html, re.I) else "lxml"
        soup = BeautifulSoup(html, parser)
        # honor <base href="..."> if present
        base_tag = soup.find('base', href=True)
        if base_tag and base_tag.get('href'):
            try:
                base_for_join = urljoin(base, base_tag['href'])
            except Exception:
                base_for_join = base
        else:
            base_for_join = base
            
        out = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("mailto:") or href.startswith("tel:"):
                continue
            try:
                norm = self._normalise(urljoin(base_for_join, href))
            except Exception:
                continue
            if self._is_same_host(norm):
                out.append(norm)

        # dedupe and preserve order
        seen = set()
        dedup = []
        for u in out:
            if u not in seen:
                seen.add(u)
                dedup.append(u)
        return dedup

    def _extract_canonical(self, html: str, base: str) -> Optional[str]:
        parser = "lxml-xml" if re.match(r"^\s*<(\?xml|rss|feed|rdf|xml)\b", html, re.I) else "lxml"
        soup = BeautifulSoup(html, parser)
        # consider <base> when resolving canonical hrefs as well
        base_tag = soup.find('base', href=True)
        if base_tag and base_tag.get('href'):
            try:
                base_for_join = urljoin(base, base_tag['href'])
            except Exception:
                base_for_join = base
        else:
            base_for_join = base

        link = soup.find("link", rel=lambda x: x and "canonical" in x.lower())
        if link and link.get("href"):
            return urljoin(base_for_join, link["href"])
        return None

    def _print_crawl_summary(self):
        total = (self.end_time - self.start_time) if self.start_time else 0.0
        avg_req = (self.total_request_duration / self.request_count) if self.request_count else 0.0
        pages_per_sec = (len(self.visited) / total) if total else 0.0
        print("---- Crawl summary ----")
        print(f"Time: {total:.2f}s, Pages visited: {len(self.visited)}, Requests: {self.request_count}")
        print(f"Success: {self.success_count}, Fail: {self.fail_count}, Retries: {self.retry_count}")
        print(f"Bytes: {self.bytes_fetched}, Avg req: {avg_req:.3f}s, Pages/sec: {pages_per_sec:.2f}")