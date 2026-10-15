"""The default wiring: real adapters and one shared httpx client, with HTTP mocked."""

import httpx
import respx

from crawler_api.main import create_app
from crawler_api.settings import Settings
from tests.helpers import finish, start

BASE = "https://example.com/"
HTML = {"content-type": "text/html; charset=utf-8"}


def mock_site() -> None:
    respx.get(f"{BASE}robots.txt").mock(return_value=httpx.Response(404))
    respx.get(BASE).mock(
        return_value=httpx.Response(
            200, headers=HTML, text='<a href="/a">a</a> <a href="https://other.org/">x</a>'
        )
    )
    respx.get(f"{BASE}a").mock(
        return_value=httpx.Response(200, headers=HTML, text='<a href="/">home</a>')
    )


@respx.mock
async def test_two_crawls_share_one_client() -> None:
    mock_site()
    app = create_app(Settings())  # no fetcher override: the default wiring
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client,
    ):
        for _ in range(2):  # the second crawl proves the first didn't close the client
            job_id = await start(client)
            status = await finish(client, job_id)
            assert status["status"] == "completed", status
            assert status["stats"]["pages"] == 2
            pages = (await client.get(f"/crawls/{job_id}/pages")).json()["items"]
            assert [page["url"] for page in pages] == [BASE, f"{BASE}a"]
            links = (await client.get(f"/crawls/{job_id}/links")).json()["items"]
            assert links == [f"{BASE}a", "https://other.org/", BASE]

    # robots.txt and both pages were requested once per crawl; other.org never.
    assert respx.calls.call_count == 6
