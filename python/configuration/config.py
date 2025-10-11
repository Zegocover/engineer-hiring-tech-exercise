from dataclasses import dataclass
from typing import Optional

@dataclass
class CrawlerConfig:
    """Configuration for the crawler service"""
    base_url: str
    
    # NETWORK TIMEOUT: How many seconds to wait for each web request
    timeout: int = 10
    
    # CONCURRENCY CONTROL: How many web pages to download simultaneously
    max_concurrency: int = 10
    
    # CACHE DURATION: How long to keep downloaded pages in memory
    cache_ttl: int = 300 # 5 minutes default
    
    # USER AGENT: How the crawler identifies itself to websites
    user_agent: str = "crawler-service/1.0 (+https://example.com)"
    
    # REDIRECT HANDLING: Whether to automatically follow HTTP redirects
    # Default: True - automatically follow when pages have moved
    follow_redirects: bool = True
    
    # CRAWL DEPTH LIMIT: Maximum "hops" away from the starting page
    max_depth: Optional[int] = None  # Optional crawl depth limit
    
    def __post_init__(self):
        """
        Validation method called automatically after object creation.
        This runs immediately after __init__ to clean and validate settings.
        """
        # Import validator here to avoid circular import issues
        from utils.validator import UrlValidator
        
        self.base_url = UrlValidator.validate(self.base_url)