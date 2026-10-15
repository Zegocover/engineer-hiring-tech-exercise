class ConfigError(ValueError):
    """Raised when a crawl is configured with invalid values."""


class FetchError(Exception):
    """Raised by a fetcher when a URL cannot be retrieved.

    The crawler records it and carries on. Any other exception raised by a
    component is treated as a bug and stops the crawl.
    """

    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"{url}: {reason}")
        self.url = url
        self.reason = reason
