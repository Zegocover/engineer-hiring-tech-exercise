import sys
import os
# Add parent directory to sys.path so we can import classes from the main codebase
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import pytest
from configuration.config import CrawlerConfig
from data.exceptions import CrawlerServiceError

class TestCrawlerConfig:
    def test_config_with_valid_url(self):
        config = CrawlerConfig(base_url="http://example.com")
        assert config.base_url == "http://example.com"

    def test_config_with_invalid_url_raises_error(self):
        # Test with a URL that will definitely fail validation (no host)
        with pytest.raises(CrawlerServiceError):
            CrawlerConfig(base_url="http://")

    def test_config_with_invalid_scheme_raises_error(self):
        # Test with invalid scheme
        with pytest.raises(CrawlerServiceError):
            CrawlerConfig(base_url="ftp://example.com")

    def test_config_with_empty_url_raises_error(self):
        # Test with empty URL
        with pytest.raises(CrawlerServiceError):
            CrawlerConfig(base_url="")

    def test_config_with_whitespace_url_raises_error(self):
        # Test with whitespace-only URL
        with pytest.raises(CrawlerServiceError):
            CrawlerConfig(base_url="   ")

    def test_config_defaults(self):
        config = CrawlerConfig(base_url="http://example.com")
        
        assert config.timeout == 10
        assert config.max_concurrency == 10
        assert config.cache_ttl == 300
        assert config.user_agent == "crawler-service/1.0 (+https://example.com)"
        assert config.follow_redirects is True
        assert config.max_depth is None

    def test_config_custom_values(self):
        config = CrawlerConfig(
            base_url="https://test.com",
            timeout=30,
            max_concurrency=5,
            cache_ttl=600,
            user_agent="test-agent/1.0",
            follow_redirects=False,
            max_depth=3
        )
        
        assert config.base_url == "https://test.com"
        assert config.timeout == 30
        assert config.max_concurrency == 5
        assert config.cache_ttl == 600
        assert config.user_agent == "test-agent/1.0"
        assert config.follow_redirects is False
        assert config.max_depth == 3

    def test_config_url_normalization(self):
        # Test that URLs without scheme get normalized
        config = CrawlerConfig(base_url="example.com")
        assert config.base_url == "http://example.com"

    def test_config_url_with_path_preserved(self):
        # Test that URL paths are preserved
        config = CrawlerConfig(base_url="https://example.com/path/to/page")
        assert config.base_url == "https://example.com/path/to/page"