from abc import ABC, abstractmethod

from web_crawler.url import URL


class WebCrawler(ABC):
    """Abstract class for web crawler. This is trivial but done for completeness."""

    @abstractmethod
    def crawl(self, url: URL | str) -> None:
        pass
