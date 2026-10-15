"""Default :class:`~site_crawler.interfaces.Writer` implementations."""

from site_crawler.writers.jsonl import JsonLinesWriter
from site_crawler.writers.text import TextWriter

__all__ = ["JsonLinesWriter", "TextWriter"]
