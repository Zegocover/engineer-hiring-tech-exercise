from typing import AsyncGenerator, Set


class Crawler:
    def __init__(self, base_url: str, concurrency: int = 10, timeout: int = 10, max_pages: int = 100) -> None:
        self.base_url = base_url

    async def crawl(self) -> AsyncGenerator[Set[str], None]:
        yield {self.base_url}