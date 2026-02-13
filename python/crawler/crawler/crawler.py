"""
Core web crawling logic.
"""
import asyncio
import re
from collections import deque
from urllib.parse import urljoin, urlparse
import urllib.robotparser # Added import

import aiohttp
from bs4 import BeautifulSoup


class WebCrawler:
    def __init__(self, start_url: str, max_concurrent_requests: int = 5):
        self.start_url = self._normalize_url(start_url)
        self.base_domain = urlparse(self.start_url).netloc
        self.visited_urls = set()
        self.to_visit_urls = deque([self.start_url])
        self.session = None  # Will be initialized in start()
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.robot_parsers = {} # Initialize robot_parsers dictionary
        print(f"Starting crawl from: {self.start_url}")
        print(f"Confined to domain: {self.base_domain}")

    async def start(self):
        async with aiohttp.ClientSession() as self.session:
            await self._crawl()

    async def _crawl(self):
        active_tasks = set()
        while self.to_visit_urls or active_tasks:
            # While there are URLs to visit AND we have capacity for new tasks
            while self.to_visit_urls and len(active_tasks) < self.semaphore._value:
                url_to_crawl = self.to_visit_urls.popleft()
                if url_to_crawl not in self.visited_urls:
                    self.visited_urls.add(url_to_crawl) # Mark as visited immediately
                    print(f"Crawling: {url_to_crawl}")
                    task = asyncio.create_task(self._fetch_and_process(url_to_crawl))
                    active_tasks.add(task)

            if not active_tasks:
                # If no active tasks and no URLs to visit, we are done
                if not self.to_visit_urls:
                    break
                # If no active tasks but URLs to visit, something is wrong with semaphore
                # or we just need to yield to the event loop.
                await asyncio.sleep(0.1) # Yield to prevent busy loop
                continue

            # Wait for at least one task to complete
            done, active_tasks = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)
            
            # The 'done' tasks would have already added new URLs to to_visit_urls or printed errors.
            # No explicit processing needed for 'done' tasks here other than removing them from active_tasks.

    async def _fetch_and_process(self, url: str):
        if not await self._is_allowed_by_robots(url):
            print(f"Skipping disallowed URL by robots.txt: {url}")
            return
        try:
            async with self.semaphore:
                async with self.session.get(url, allow_redirects=True, timeout=10) as response:
                    response.raise_for_status()  # Raise an exception for bad status codes
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/html' in content_type:
                        html = await response.text()
                        found_links = self._extract_links(html, url)
                        for link in found_links:
                            if self._is_same_domain(link) and link not in self.visited_urls:
                                self.to_visit_urls.append(link)
                    else:
                        print(f"Skipping non-HTML content for {url} ({content_type})")
        except aiohttp.ClientError as e:
            print(f"Error fetching {url}: {e}")
        except asyncio.TimeoutError:
            print(f"Timeout fetching {url}")
        except Exception as e:
            print(f"An unexpected error occurred for {url}: {e}")

    def _extract_links(self, html: str, base_url: str) -> set[str]:
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(base_url, href)
            normalized_url = self._normalize_url(full_url)
            if normalized_url:
                links.add(normalized_url)
        return links

    def _normalize_url(self, url: str) -> str:
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # Remove trailing slash from the path, unless the path is the root (i.e., "/")
        if path.endswith('/') and len(path) > 1:
            path = path.rstrip('/')
        elif path == '/': # If path is exactly '/', normalize it to empty string
            path = ''
        
        return parsed_url._replace(fragment='', path=path).geturl()

    def _is_same_domain(self, url: str) -> bool:
        return urlparse(url).netloc == self.base_domain

    async def _is_allowed_by_robots(self, url: str) -> bool:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path or '/'

        if domain not in self.robot_parsers:
            await self._fetch_robots_txt(domain)
        
        # User-agent should be specific to your crawler, e.g., "SimpleWebCrawler"
        # For simplicity, using a generic user agent here.
        # In a real-world scenario, you might want to configure this.
        return self.robot_parsers[domain].can_fetch("*", url)

    async def _fetch_robots_txt(self, domain: str):
        if domain in self.robot_parsers:
            return

        robotparser = urllib.robotparser.RobotFileParser()
        robots_txt_url = urljoin(f"http://{domain}", "/robots.txt")
        robotparser.set_url(robots_txt_url)

        try:
            async with self.semaphore:
                async with self.session.get(robots_txt_url, allow_redirects=True, timeout=5) as response:
                    response.raise_for_status()
                    robots_content = await response.text()
                    robotparser.parse(robots_content.splitlines())
                    self.robot_parsers[domain] = robotparser
                    print(f"Successfully fetched and parsed robots.txt for {domain}")
        except aiohttp.ClientError as e:
            print(f"Could not fetch robots.txt for {domain}: {e}. Assuming full access.")
            # If robots.txt cannot be fetched, assume full access by storing a parser that allows all.
            robotparser.parse("") 
            self.robot_parsers[domain] = robotparser
        except asyncio.TimeoutError:
            print(f"Timeout fetching robots.txt for {domain}. Assuming full access.")
            robotparser.parse("")
            self.robot_parsers[domain] = robotparser
        except Exception as e:
            print(f"An unexpected error occurred while fetching robots.txt for {domain}: {e}. Assuming full access.")
            robotparser.parse("")
            self.robot_parsers[domain] = robotparser
