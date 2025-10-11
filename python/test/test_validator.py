
import sys
import os
# Add parent directory to sys.path so we can import classes from the main codebase
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import pytest
from utils.validator import UrlValidator
from data.exceptions import CrawlerServiceError

class TestUrlValidator:
    def test_valid_http_url(self):
        url = "http://example.com"
        result = UrlValidator.validate(url)
        assert result == "http://example.com"

    def test_valid_https_url(self):
        url = "https://example.com"
        result = UrlValidator.validate(url)
        assert result == "https://example.com"

    def test_url_without_scheme_gets_http(self):
        url = "example.com"
        result = UrlValidator.validate(url)
        assert result == "http://example.com"

    def test_url_with_path(self):
        url = "https://example.com/path/to/page"
        result = UrlValidator.validate(url)
        assert result == "https://example.com/path/to/page"

    def test_empty_string_raises_error(self):
        with pytest.raises(CrawlerServiceError, match="URL must be a non-empty string"):
            UrlValidator.validate("")

    def test_whitespace_only_raises_error(self):
        with pytest.raises(CrawlerServiceError, match="URL must be a non-empty string"):
            UrlValidator.validate("   ")

    def test_none_raises_error(self):
        with pytest.raises(CrawlerServiceError, match="URL must be a non-empty string"):
            UrlValidator.validate(None)

    def test_invalid_scheme_raises_error(self):
        with pytest.raises(CrawlerServiceError, match="URL must use http or https scheme"):
            UrlValidator.validate("ftp://example.com")

    def test_malformed_url_raises_error(self):
        with pytest.raises(CrawlerServiceError, match="Malformed URL: missing host"):
            UrlValidator.validate("http://")

    def test_url_with_whitespace_gets_stripped(self):
        url = "  https://example.com  "
        result = UrlValidator.validate(url)
        assert result == "https://example.com"
