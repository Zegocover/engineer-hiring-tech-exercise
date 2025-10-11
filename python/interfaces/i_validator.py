from abc import ABC, abstractmethod

class IUrlValidator(ABC):
    """Abstract interface for URL validation."""

    @abstractmethod
    def validate(self, url: str) -> str:
        """Validate and normalize a URL. Return the normalized URL."""
        pass