"""
Crawler Module
--------------

This module contains the core `Crawler` class which manages the crawling process.
It handles:
- URL Queue management (Producer-Consumer pattern)
- Rate limiting (via TokenBucket)
- Robots.txt parsing and enforcement
- Async HTTP data fetching
"""
import asyncio
import aiohttp
from typing import Set, List
import logging
import random
import csv
from .parser import extract_links
from .utils import async_retry
import ssl
import certifi
import time
from urllib.parse import urlparse, urljoin
import urllib.robotparser

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TokenBucket:
    """
    Implements a token bucket algorithm for rate limiting.
    
    Attributes:
        rate (float): The rate at which tokens are refilled (tokens per second).
        capacity (float): The maximum number of tokens the bucket can hold.
        tokens (float): Current number of available tokens.
        last_update (float): Timestamp of the last token refill.
    """
    def __init__(self, rate, capacity):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()

    async def acquire(self):
        if self.rate <= 0:
            return # No rate limit
            
        while True:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            
            if self.tokens >= 1:
                self.tokens -= 1
                return
            
            wait_time = (1 - self.tokens) / self.rate
            if wait_time > 0:
                await asyncio.sleep(wait_time)

class Crawler:
    """
    Main crawler class that manages the crawling state and logic.
    
    It uses a producer-consumer pattern with asyncio queues to crawl URLs concurrently.
    
    Attributes:
        base_url (str): The starting URL and the domain boundary.
        concurrency (int): Number of concurrent worker tasks.
        output_file (str): Path to the CSV output file.
        rate_limit (float): Requests per second limit.
    """
    def __init__(self, base_url: str, concurrency: int = 10, output_file: str = "results.csv", rate_limit: float = 5.0):
        self.base_url = base_url
        self.concurrency = concurrency
        self.output_file = output_file
        self.rate_limit = rate_limit
        self.visited: Set[str] = set()
        self.queue: asyncio.Queue = asyncio.Queue()
        self.write_queue: asyncio.Queue = asyncio.Queue()
        self.session: aiohttp.ClientSession = None
        self.limiter = TokenBucket(rate_limit, rate_limit)
        self.rp = urllib.robotparser.RobotFileParser()
        self.robots_txt_url = urljoin(base_url, "/robots.txt")

    async def init_robots_txt(self):
        """Fetches and parses robots.txt."""
        logger.info(f"Fetching robots.txt from {self.robots_txt_url}")
        try:
            # We use our own fetch (with retries) but bypassing rate limit for robots.txt 
            # Or just use raw session get to avoid limiter if we want startup to be fast
            # But politeness applies to robots.txt too. Let's use raw session for simplicity without decorator 
            # or just reuse fetch logic. 
            
            # Note: We need to handle potential 404 here gracefully (allow all).
            async with self.session.get(self.robots_txt_url, timeout=10) as response:
                if response.status == 200:
                    text = await response.text()
                    self.rp.parse(text.splitlines())
                    logger.info("Parsed robots.txt successfully.")
                else:
                    logger.warning(f"Could not fetch robots.txt (Status {response.status}). Assuming full access.")
                    self.rp.allow_all = True
        except Exception as e:
            logger.warning(f"Error fetching robots.txt: {e}. Assuming full access.")
            self.rp.allow_all = True
            
    def can_fetch(self, url: str) -> bool:
        return self.rp.can_fetch("*", url)

    async def writer(self):
        """Consumes results from write_queue and writes to CSV."""
        with open(self.output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Source URL', 'Found Link'])
            
            while True:
                item = await self.write_queue.get()
                if item is None:
                    self.write_queue.task_done()
                    break
                
                # Write to file in a separate thread to avoid blocking the event loop
                await asyncio.to_thread(writer.writerow, item)
                self.write_queue.task_done()

    @async_retry(retries=3, backoff_factor=2)
    async def fetch(self, url: str) -> (str, str):
        await self.limiter.acquire()
        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status >= 500 or response.status == 429:
                    # Trigger retry for server errors and rate limits
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status,
                        message="Server Error or Rate Limit",
                        headers=response.headers
                    )
                
                if response.status >= 400:
                    logger.warning(f"Skipping {url}: HTTP {response.status}")
                    return "", url

                final_url = str(response.url)
                if response.status == 200 and 'text/html' in response.headers.get('Content-Type', ''):
                    html = await response.text()
                    return html, final_url
        except Exception as e:
            # Let the decorator handle re-raisable network errors, but catch unexpected ones
            if isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)):
                raise e
            logger.error(f"Unexpected error fetching {url}: {e}")
        return "", url

    async def worker(self):
        while True:
            url = await self.queue.get()
            if url in self.visited:
                self.queue.task_done()
                continue
                
            if not self.can_fetch(url):
                logger.warning(f"Skipping {url}: Disallowed by robots.txt")
                self.queue.task_done()
                continue
            
            self.visited.add(url)
            
            from .utils import is_same_domain
            
            html, final_url = await self.fetch(url)
            
            if html:
                # Check if redirect took us to a different domain
                if not is_same_domain(self.base_url, final_url):
                     logger.warning(f"Skipping {final_url}: Redirected to different domain")
                     self.queue.task_done()
                     continue

                links = extract_links(html, final_url) # Use final_url as base
                logger.info(f"Found: {url} -> {len(links)} links")
                
                for link in links:
                    if link not in self.visited:
                        await self.queue.put(link)
                    # We log all found links, even if previously visited (optional choice, but standard for a crawler output)
                    # Or should we only log new ones? The prompt says "print... all the URLs it finds on that page"
                    await self.write_queue.put((url, link))
            
            self.queue.task_done()

    async def crawl(self):
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context))
        
        await self.init_robots_txt()
        
        writer_task = asyncio.create_task(self.writer())
        
        try:
            self.queue.put_nowait(self.base_url)
            workers = [asyncio.create_task(self.worker()) for _ in range(self.concurrency)]
            
            # Wait for the queue to be fully processed
            await self.queue.join()
            
            for w in workers:
                w.cancel()
                
            # Signal writer to stop
            await self.write_queue.put(None)
            await self.write_queue.join()
            await writer_task
            
            print(f"Total URLs crawled: {len(self.visited)}")
            print(f"Results written to: {self.output_file}")
            
        finally:
            await self.session.close()
