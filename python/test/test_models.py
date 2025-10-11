import sys
import os
# Add parent directory to sys.path so we can import classes from the main codebase
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from datetime import datetime, timedelta
from data.models import CrawlResult, CrawlSummary

class TestCrawlResult:
    def test_crawl_result_defaults(self):
        result = CrawlResult(url="http://example.com")
        
        assert result.url == "http://example.com"
        assert result.links == []
        assert result.status_code is None
        assert result.error is None
        assert isinstance(result.timestamp, datetime)
        assert result.content_length is None

    def test_crawl_result_with_data(self):
        timestamp = datetime.now()
        result = CrawlResult(
            url="http://example.com",
            links=["http://example.com/page1", "http://example.com/page2"],
            status_code=200,
            content_length=1024,
            timestamp=timestamp
        )
        
        assert result.url == "http://example.com"
        assert len(result.links) == 2
        assert result.status_code == 200
        assert result.content_length == 1024
        assert result.timestamp == timestamp

class TestCrawlSummary:
    def test_crawl_summary_defaults(self):
        summary = CrawlSummary(base_url="http://example.com")
        
        assert summary.base_url == "http://example.com"
        assert summary.total_pages == 0
        assert summary.successful_pages == 0
        assert summary.failed_pages == 0
        assert summary.total_links == 0
        assert summary.unique_links == 0
        assert isinstance(summary.start_time, datetime)
        assert summary.end_time is None
        assert summary.errors == []

    def test_duration_calculation(self):
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=45, microseconds=500000)
        
        summary = CrawlSummary(
            base_url="http://example.com",
            start_time=start_time,
            end_time=end_time
        )
        
        duration = summary.duration
        assert duration is not None
        assert 45.0 <= duration <= 46.0

    def test_duration_none_when_not_finished(self):
        summary = CrawlSummary(base_url="http://example.com")
        assert summary.duration is None

    def test_crawl_summary_with_data(self):
        errors = ["Error 1", "Error 2"]
        summary = CrawlSummary(
            base_url="http://example.com",
            total_pages=10,
            successful_pages=8,
            failed_pages=2,
            total_links=50,
            unique_links=45,
            errors=errors
        )
        
        assert summary.total_pages == 10
        assert summary.successful_pages == 8
        assert summary.failed_pages == 2
        assert summary.total_links == 50
        assert summary.unique_links == 45
        assert summary.errors == errors