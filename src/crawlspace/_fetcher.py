from httpx import AsyncClient, HTTPError, HTTPStatusError

from .schemas import FetchResult


class Fetcher:
    @staticmethod
    async def fetch(url: str):
        client = AsyncClient()
        try:
            response = await client.get(url)
            return FetchResult(url=url, status=response.status_code, text=response.text)

        except Exception:
            return FetchResult(url=url, status=-1, text="")
