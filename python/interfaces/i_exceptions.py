from abc import ABC

class ICrawlerServiceError(ABC, Exception):
    """Abstract base class for all crawler service errors."""
    pass