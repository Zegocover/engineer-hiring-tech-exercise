import sys
import os
# Add parent directory to sys.path so we can import classes from the main codebase
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock
from core.http_fetcher import HttpFetcher, FetchResult, CacheEntry
from data.exceptions import CrawlerServiceError

class TestHttpFetcher:
    @pytest.fixture
    def fetcher(self):
        return HttpFetcher(timeout=5, cache_ttl=60)

    @pytest.fixture
    def mock_client(self):
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_successful_fetch(self, fetcher, mock_client):
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.headers = {"content-type": "text/html"}
        mock_client.get.return_value = mock_response

        result = await fetcher.fetch(mock_client, "http://example.com")

        assert isinstance(result, FetchResult)
        assert result.url == "http://example.com"
        assert result.content == "<html><body>Test</body></html>"
        assert result.status_code == 200
        assert result.headers == {"content-type": "text/html"}
        assert result.from_cache is False
        assert result.response_time is not None

    @pytest.mark.asyncio
    async def test_cached_fetch(self, fetcher, mock_client):
        # First fetch
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.headers = {"content-type": "text/html"}
        mock_client.get.return_value = mock_response

        # First request
        result1 = await fetcher.fetch(mock_client, "http://example.com")
        
        # Second request (should be cached)
        result2 = await fetcher.fetch(mock_client, "http://example.com")

        assert result1.from_cache is False
        assert result2.from_cache is True
        assert result1.content == result2.content
        assert mock_client.get.call_count == 1  # Only called once

    @pytest.mark.asyncio
    async def test_http_error_raises_exception(self, fetcher, mock_client):
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response

        with pytest.raises(CrawlerServiceError, match="HTTP error 404"):
            await fetcher.fetch(mock_client, "http://example.com/notfound")

    @pytest.mark.asyncio
    async def test_request_error_raises_exception(self, fetcher, mock_client):
        # Mock network error
        mock_client.get.side_effect = httpx.RequestError("Network error")

        with pytest.raises(CrawlerServiceError, match="Failed to fetch"):
            await fetcher.fetch(mock_client, "http://example.com")

    def test_cache_entry_structure(self):
        entry = CacheEntry(
            content="<html>test</html>",
            status_code=200,
            headers={"content-type": "text/html"},
            timestamp=1234567890.0,
            response_time=0.123
        )
        
        assert entry.content == "<html>test</html>"
        assert entry.status_code == 200
        assert entry.headers == {"content-type": "text/html"}
        assert entry.timestamp == 1234567890.0
        assert entry.response_time == 0.123

    def test_fetch_result_structure(self):
        from datetime import datetime
        
        result = FetchResult(
            url="http://example.com",
            content="<html>test</html>",
            status_code=200,
            headers={"content-type": "text/html"},
            from_cache=True,
            response_time=0.123
        )
        
        assert result.url == "http://example.com"
        assert result.content == "<html>test</html>"
        assert result.status_code == 200
        assert result.from_cache is True
        assert result.response_time == 0.123
        assert isinstance(result.timestamp, datetime)
