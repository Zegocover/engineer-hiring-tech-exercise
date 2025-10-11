from abc import abstractmethod, ABC

class ICrawlerService(ABC):
    """Abstract base class defining the crawler interface."""

    @abstractmethod
    def __init__(self, base_url: str, timeout: int, max_concurrency: int, cache_ttl: int):
        """Initialize crawler with base URL, timeout, concurrency, and cache TTL."""
        pass

    @abstractmethod
    async def crawl(self):
        """Run the asynchronous crawl process."""
        pass

    @abstractmethod
    def run(self):
        """Run the crawler in a synchronous context."""
        pass