from __future__ import annotations


class SiteCrawler:
    def __init__(
        self,
        base_url: str,
        *,
        batch_size: int = 10,
        max_depth: int | None = None,
        max_urls: int | None = None,
        timeout: float = 10.0,
        retries: int = 1,
        output: str | None = None,
        output_format: str = "text",
    ) -> None:
        if batch_size < 1 or batch_size > 10:
            raise ValueError("batch_size must be between 1 and 10")
        if max_urls is not None and (max_urls < 1 or max_urls > 1000):
            raise ValueError("max_urls must be between 1 and 1000")
        if timeout < 0 or timeout > 10:
            raise ValueError("timeout must be between 0 and 10")
        if retries < 0 or retries > 3:
            raise ValueError("retries must be between 0 and 3")

        self.base_url = base_url
        self.batch_size = batch_size
        self.max_depth = max_depth
        self.max_urls = max_urls
        self.timeout = timeout
        self.retries = retries
        self.output = output
        self.output_format = output_format

    def crawl(self) -> None:
        return None
