from httpx import AsyncClient

from .schemas import FetchResult


class Fetcher:
    @staticmethod
    async def fetch(url: str):
        async with AsyncClient() as client:
            try:
                response = await client.head(url)

                content_type = response.headers.get("content-type", "")
                if "text" in content_type:
                    response = await client.get(url)
                    return FetchResult(
                        url=url, status=response.status_code, text=response.text
                    )
                else:
                    return FetchResult(url=url, status=response.status_code, text="")

            except Exception:
                return FetchResult(url=url, status=-1, text="")
