import asyncio
import httpx
from datetime import datetime
from typing import List

from core.http_fetcher import HttpFetcher, FetchResult
from interfaces.i_crawler_service import ICrawlerService
from core.link_parser import LinkParser
from configuration.config import CrawlerConfig
from data.models import CrawlResult, CrawlSummary
from data.exceptions import CrawlerServiceError

class CrawlerService(ICrawlerService):
    def __init__(self, config: CrawlerConfig):
        # Store the configuration
        self.config = config
        
        # Parse the base URL to extract components like domain
        self.parsed_base = httpx.URL(config.base_url)
        
        # Extract just the domain name
        self.domain = self.parsed_base.host

        # Set to keep track of URLs we've already visited
        self.visited = set()
        
        # Async queue to store URLs that need to be crawled
        self.to_visit = asyncio.Queue()
        
        # List to store results from each page we crawl
        self.results: List[CrawlResult] = []
        
        # Summary object to track overall crawling statistics
        self.summary = CrawlSummary(base_url=config.base_url)

        # HttpFetcher handles downloading web pages with caching
        self.fetcher = HttpFetcher(timeout=config.timeout, cache_ttl=config.cache_ttl)
        
        # LinkParser extracts and filters links from HTML content
        self.parser = LinkParser(domain=self.domain)

    async def _worker(self, client: httpx.AsyncClient, semaphore: asyncio.Semaphore):
        """
        Worker function that processes URLs from the queue.
        Multiple workers run concurrently to speed up crawling.
        """
        while True:
            # Get the next URL from the queue 
            url = await self.to_visit.get()
            
            # duplicate check
            if url in self.visited:
                # Mark this queue item as done and continue to next URL
                self.to_visit.task_done()
                continue
                
            # Mark this URL as visited so we don't crawl it again
            self.visited.add(url)

            # semaphore limit's concurrent requests
            async with semaphore:
                # store what we find on this page
                result = CrawlResult(url=url)
                
                try:
                    #fetch the web page content
                    fetch_result: FetchResult = await self.fetcher.fetch(client, url)
                    
                    # Store the HTTP status code
                    result.status_code = fetch_result.status_code
                    
                    # Store how large the page content is in bytes
                    result.content_length = len(fetch_result.content)
                    
                    # Extract all links from the HTML content of this page
                    links = self.parser.extract_links(fetch_result.content, url)
                    
                    # Store the links we found in the result
                    result.links = links
                    
                    # Update our summary statistics
                    self.summary.successful_pages += 1  # Count successful page
                    self.summary.total_links += len(links)  # Count total links found
                    
                    print(f"\nPage: {url} ({fetch_result.status_code})")
                    for link in links:
                        print(f"  Link: {link}")
                        
                        # Add new links to our queue
                        if link not in self.visited:
                            await self.to_visit.put(link)
                            
                except CrawlerServiceError as e:
                    result.error = str(e)
                    self.summary.failed_pages += 1
                    self.summary.errors.append(f"{url}: {e}")
                    print(f"Error crawling {url}: {e}")
                    
                finally:
                    self.results.append(result)
                    self.summary.total_pages += 1
                    self.to_visit.task_done()

    async def crawl(self) -> CrawlSummary:
        # Add the starting URL to our queue
        await self.to_visit.put(self.config.base_url)

        # Create HTTP client with our configuration settings
        async with httpx.AsyncClient(
            headers={"User-Agent": self.config.user_agent},  # Identify our crawler
            follow_redirects=self.config.follow_redirects    # Handle URL redirects
        ) as client:
            
            # limit concurrent requests
            semaphore = asyncio.Semaphore(self.config.max_concurrency)
            
            # Start multiple worker tasks to process URLs concurrently
            workers = [
                asyncio.create_task(self._worker(client, semaphore)) 
                for _ in range(self.config.max_concurrency)
            ]
            
            # Wait until all URLs in the queue have been processed
            await self.to_visit.join()
            
            # Cancel all worker tasks when done
            for w in workers:
                w.cancel()

        # Mark when we finished crawling
        self.summary.end_time = datetime.now()
        
        # Calculate how many unique links we found across all pages (remove duplicates)
        self.summary.unique_links = len(set(
            link for result in self.results for link in result.links
        ))
        
        return self.summary

    def run(self) -> CrawlSummary:
        try:
            return asyncio.run(self.crawl())
            
        except KeyboardInterrupt:
            print("Crawler stopped by user.")
            self.summary.end_time = datetime.now()
            return self.summary

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python crawler_service.py <base_url>")
        sys.exit(1)
    config = CrawlerConfig(base_url=sys.argv[1], max_concurrency=10)
    
    crawler = CrawlerService(config)
    summary = crawler.run()
    
    print(f"\nCrawl Summary:")
    print(f"Total pages: {summary.total_pages}")
    print(f"Successful: {summary.successful_pages}")
    print(f"Failed: {summary.failed_pages}")
    
    print(f"Duration: {summary.duration:.2f}s" if summary.duration else "Duration: N/A")
