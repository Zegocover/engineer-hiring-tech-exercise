"""Extension points of the crawler.

Consumers replace how pages are fetched, how links are extracted and where
results go by passing any object that structurally matches these protocols.
No subclassing or registration is required.
"""

from site_crawler.interfaces.fetcher import Fetcher
from site_crawler.interfaces.parser import Parser
from site_crawler.interfaces.writer import Writer

__all__ = ["Fetcher", "Parser", "Writer"]
