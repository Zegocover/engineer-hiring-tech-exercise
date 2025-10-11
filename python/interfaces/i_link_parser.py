from abc import ABC, abstractmethod
from typing import List

class ILinkParser(ABC):
    """Abstract interface for HTML link parsers."""

    @abstractmethod
    def extract_links(self, html: str, current_url: str) -> List[str]:
        """Extract and return links from HTML content."""
        pass