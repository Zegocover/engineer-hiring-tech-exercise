from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class CrawlResult:
    """Results from crawling a single page"""
    url: str
    links: List[str] = field(default_factory=list)
    status_code: Optional[int] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    content_length: Optional[int] = None

@dataclass
class CrawlSummary:
    """Summary of entire crawl session"""
    base_url: str
    total_pages: int = 0
    successful_pages: int = 0
    failed_pages: int = 0
    total_links: int = 0
    unique_links: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate crawl duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None