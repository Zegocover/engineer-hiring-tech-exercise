import sys
import os
# Add parent directory to sys.path so we can import classes from the main codebase
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from core.crawler_service import CrawlerService
from configuration.config import CrawlerConfig
from data.models import CrawlResult, CrawlSummary
from core.http_fetcher import FetchResult
from data.exceptions import CrawlerServiceError

class TestCrawlerService:
    @pytest.fixture
    def config(self):
        return CrawlerConfig(
            base_url="http://example.com",
            timeout=5,
            max_concurrency=2,
            cache_ttl=60
        )

    @pytest.fixture
    def crawler(self, config):
        return CrawlerService(config)

    def test_crawler_initialization(self, config):
        crawler = CrawlerService(config)
        
        assert crawler.config.base_url == "http://example.com"
        assert crawler.config.timeout == 5
        assert crawler.config.max_concurrency == 2
        assert crawler.domain == "example.com"
        assert isinstance(crawler.summary, CrawlSummary)
        assert crawler.summary.base_url == "http://example.com"

    def test_config_validation(self):
        # Test that invalid URL gets validated during config creation
        with pytest.raises(CrawlerServiceError):
            CrawlerConfig(base_url="http://")  # Missing host

    def test_config_validation_empty_url(self):
        # Test empty URL validation
        with pytest.raises(CrawlerServiceError):
            CrawlerConfig(base_url="")

    def test_config_validation_invalid_scheme(self):
        # Test invalid scheme validation
        with pytest.raises(CrawlerServiceError):
            CrawlerConfig(base_url="ftp://example.com")

    def test_config_defaults(self):
        config = CrawlerConfig(base_url="http://example.com")
        
        assert config.timeout == 10
        assert config.max_concurrency == 10
        assert config.cache_ttl == 300
        assert config.user_agent == "crawler-service/1.0 (+https://example.com)"
        assert config.follow_redirects is True

    @pytest.mark.asyncio
    async def test_successful_crawl(self, crawler):
        # Mock the fetcher and parser
        mock_fetch_result = FetchResult(
            url="http://example.com",
            content="<html><body><a href='http://example.com/page1'>Page 1</a></body></html>",
            status_code=200,
            headers={"content-type": "text/html"}
        )
        
        with patch.object(crawler.fetcher, 'fetch', return_value=mock_fetch_result) as mock_fetch, \
             patch.object(crawler.parser, 'extract_links', return_value=["http://example.com/page1"]) as mock_extract:
            
            summary = await crawler.crawl()
            
            assert isinstance(summary, CrawlSummary)
            assert summary.total_pages >= 1
            assert summary.successful_pages >= 1
            assert summary.failed_pages == 0
            assert summary.end_time is not None
            assert len(crawler.results) >= 1
            assert isinstance(crawler.results[0], CrawlResult)

    @pytest.mark.asyncio
    async def test_crawl_with_error(self, crawler):
        # Mock fetcher to raise an exception
        with patch.object(crawler.fetcher, 'fetch', side_effect=CrawlerServiceError("Test error")):
            summary = await crawler.crawl()
            
            assert summary.failed_pages >= 1
            assert len(summary.errors) >= 1
            assert "Test error" in summary.errors[0]

    def test_run_method(self, crawler):
        # Mock the crawl method
        mock_summary = CrawlSummary(base_url="http://example.com", total_pages=1)
        
        with patch.object(crawler, 'crawl', return_value=mock_summary) as mock_crawl:
            result = crawler.run()
            
            assert result == mock_summary
            mock_crawl.assert_called_once()

    def test_crawl_result_structure(self):
        result = CrawlResult(
            url="http://example.com",
            links=["http://example.com/page1"],
            status_code=200,
            content_length=1024
        )
        
        assert result.url == "http://example.com"
        assert result.links == ["http://example.com/page1"]
        assert result.status_code == 200
        assert result.content_length == 1024
        assert result.error is None
        assert result.timestamp is not None

    def test_crawl_summary_properties(self):
        from datetime import datetime, timedelta
        
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)
        
        summary = CrawlSummary(
            base_url="http://example.com",
            total_pages=10,
            successful_pages=8,
            failed_pages=2,
            start_time=start_time,
            end_time=end_time
        )
        
        assert summary.duration == 30.0
        assert summary.total_pages == 10
        assert summary.successful_pages == 8
        assert summary.failed_pages == 2

    def test_crawl_summary_duration_none_when_not_finished(self):
        summary = CrawlSummary(base_url="http://example.com")
        assert summary.duration is None

    @pytest.mark.asyncio
    async def test_worker_handles_duplicate_urls(self, crawler):
        """Test that worker correctly handles URLs that are already visited"""
        # Add URL to visited set
        test_url = "http://example.com/test"
        crawler.visited.add(test_url)
        
        # Add same URL to queue  
        await crawler.to_visit.put(test_url)
        
        # Mock client and semaphore
        mock_client = AsyncMock()
        mock_semaphore = AsyncMock()
        
        # Mock the fetcher to track if it was called
        with patch.object(crawler.fetcher, 'fetch') as mock_fetch:
            # Create worker task
            worker_task = asyncio.create_task(crawler._worker(mock_client, mock_semaphore))
            
            # Give the worker a moment to process
            await asyncio.sleep(0.1)
            
            # Cancel worker
            worker_task.cancel()
            
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
            
            # Verify fetcher was not called (URL was skipped)
            mock_fetch.assert_not_called()

    @pytest.mark.asyncio 
    async def test_worker_processes_new_url(self, crawler):
        """Test that worker processes URLs that haven't been visited"""
        test_url = "http://example.com/test"
        
        # Add URL to queue (but not to visited set)
        await crawler.to_visit.put(test_url)
        
        # Mock client and semaphore
        mock_client = AsyncMock()
        mock_semaphore = AsyncMock()
        
        # Mock successful fetch result
        mock_fetch_result = FetchResult(
            url=test_url,
            content="<html><body>Test</body></html>",
            status_code=200
        )
        
        with patch.object(crawler.fetcher, 'fetch', return_value=mock_fetch_result) as mock_fetch, \
             patch.object(crawler.parser, 'extract_links', return_value=[]) as mock_extract:
            
            # Create worker task
            worker_task = asyncio.create_task(crawler._worker(mock_client, mock_semaphore))
            
            # Wait for queue to be processed
            await crawler.to_visit.join()
            
            # Cancel worker
            worker_task.cancel()
            
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
            
            # Verify fetcher was called
            mock_fetch.assert_called_once_with(mock_client, test_url)
            # Verify URL was added to visited set
            assert test_url in crawler.visited
            # Verify result was added
            assert len(crawler.results) == 1
            assert crawler.results[0].url == test_url