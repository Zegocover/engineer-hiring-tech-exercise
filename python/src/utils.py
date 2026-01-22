"""
Utils Module
------------

Helper functions for URL normalization, validation, and decorators.
Includes:
- url_normalization: Handling relative URLs and fragments.
- is_same_domain: Ensuring the crawler stays within boundary.
- async_retry: Decorator for robust error handling.
"""
from urllib.parse import urlparse, urljoin, urldefrag

def normalize_url(base_url: str, url: str) -> str:
    """
    Resolves relative URLs to absolute URLs and removes fragments.
    """
    # Join with base to handle relative URLs
    absolute_url = urljoin(base_url, url)
    # Remove fragment identifier
    absolute_url, _ = urldefrag(absolute_url)
    return absolute_url

def is_same_domain(base_url: str, url: str) -> bool:
    """
    Checks if the URL belongs to the same domain as the base URL.
    Strictly checks the netloc.
    """
    base_netloc = urlparse(base_url).netloc
    url_netloc = urlparse(url).netloc
    
    # Handle cases where netloc might be empty (relative URLs should be normalized first)
    if not url_netloc:
        return False
        
    return base_netloc == url_netloc

import functools
import logging
import random
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

def async_retry(retries=3, backoff_factor=1.5):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            delay = 1
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    if i == retries - 1:
                        logger.error(f"Failed after {retries} attempts: {e}")
                        raise
                    sleep_time = delay * (backoff_factor ** i) + random.uniform(0, 1)
                    logger.warning(f"Attempt {i+1} failed: {e}. Retrying in {sleep_time:.2f}s...")
                    await asyncio.sleep(sleep_time)
        return wrapper
    return decorator
