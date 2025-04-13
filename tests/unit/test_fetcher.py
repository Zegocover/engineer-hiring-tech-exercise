from crawlspace._fetcher import Fetcher
from crawlspace.schemas import FetchResult


async def test_fetcher():
    fetcher = Fetcher()

    url: str = "http://localhost:8888"
    result: FetchResult = await fetcher.fetch(url)

    assert result == FetchResult(url=url, status=200, text="")
