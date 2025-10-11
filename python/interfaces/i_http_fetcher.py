from abc import abstractmethod, ABC
import httpx

class IHttpFetcher(ABC):
    """Abstract interface for HTTP fetchers."""

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient, url: str) -> str:
        """Fetch the content of a URL asynchronously."""
        pass
