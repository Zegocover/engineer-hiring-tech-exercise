from .schemas import FetchResult


class Fetcher:
    @staticmethod
    async def fetch(url: str):
        return FetchResult(url=url, status=200, text="")
