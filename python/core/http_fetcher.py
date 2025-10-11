from dataclasses import dataclass, field
import time
import httpx
from typing import Dict, Optional
from datetime import datetime

from data.exceptions import CrawlerServiceError
from interfaces.i_http_fetcher import IHttpFetcher

@dataclass
class FetchResult:
    url: str
    #The HTML/text content
    content: str
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    # True if this came from our cache, False if we downloaded it fresh
    from_cache: bool = False
    response_time: Optional[float] = None

@dataclass
class CacheEntry:
    content: str
    status_code: int
    headers: Dict[str, str]
    timestamp: float
    response_time: float

class HttpFetcher(IHttpFetcher):
    def __init__(self, timeout: int = 10, cache_ttl: int = 300):
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        
        # Create empty cache dictionary to store downloaded pages
        self._cache: Dict[str, CacheEntry] = {}

    def _is_cache_valid(self, url: str) -> bool:
        # First check: do we even have this URL cached?
        if url not in self._cache:
            return False
            
        entry = self._cache[url]
        # Second check: is the cached entry still fresh?
        return (time.time() - entry.timestamp) < self.cache_ttl

    async def fetch(self, client: httpx.AsyncClient, url: str) -> FetchResult:
        # Step 1: Check if we have a fresh cached copy
        if self._is_cache_valid(url):
            # Get the cached entry
            entry = self._cache[url]
            
            # Return cached content wrapped in a FetchResult
            return FetchResult(
                url=url,                         
                content=entry.content,             
                status_code=entry.status_code,     
                headers=entry.headers,             
                from_cache=True,                   
                response_time=entry.response_time  
            )

        # Step 2: Cache miss or expired - need to fetch fresh content
        try:
            # Record when we start the request
            start_time = time.time()
            
            resp = await client.get(url, timeout=self.timeout)
            
            response_time = time.time() - start_time
            
            if resp.status_code >= 400:
                raise CrawlerServiceError(f"HTTP error {resp.status_code} on {url}")
            
            # Step 3: Extract data from the response
            content = resp.text
            
            headers = dict(resp.headers)
            
            # Step 4: Store in cache for future requests
            self._cache[url] = CacheEntry(
                content=content,                
                status_code=resp.status_code,   
                headers=headers,                
                timestamp=time.time(),          
                response_time=response_time
            )

            # Step 5: Return the result
            return FetchResult(
                url=url,                        
                content=content,
                status_code=resp.status_code,
                headers=headers,
                response_time=response_time
            )
            
        except httpx.RequestError as e:
            raise CrawlerServiceError(f"Failed to fetch {url}: {e}") from e