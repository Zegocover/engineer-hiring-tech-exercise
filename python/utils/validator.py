from urllib.parse import urlparse
from data.exceptions import CrawlerServiceError
from interfaces.i_validator import IUrlValidator

class UrlValidator(IUrlValidator):
    """Validates and normalizes URLs"""

    @staticmethod
    def validate(url: str) -> str:
        """Validate URL and return normalized version with scheme"""
        if not isinstance(url, str) or not url.strip():
            raise CrawlerServiceError("URL must be a non-empty string")

        url = url.strip()
        parsed = urlparse(url)

        if not parsed.scheme:
            url = "http://" + url  # Default to http if scheme missing
            parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            raise CrawlerServiceError("URL must use http or https scheme")

        if not parsed.netloc:
            raise CrawlerServiceError("Malformed URL: missing host")

        return url
