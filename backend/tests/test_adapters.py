from collections.abc import AsyncIterator

import httpx
import pytest
import respx
from site_crawler.models import CrawlConfig, PageResult

from crawler_api.adapters import JobWriter, SharedClientFetcher
from crawler_api.jobs import CrawlJob

URL = "https://example.com/"


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(follow_redirects=True) as c:
        yield c


@respx.mock
async def test_fetch_uses_shared_client(client: httpx.AsyncClient) -> None:
    respx.get(URL).mock(
        return_value=httpx.Response(200, headers={"content-type": "text/html"}, text="<p>hi</p>")
    )
    result = await SharedClientFetcher(client).fetch(URL)
    assert result.status == 200
    assert result.body == b"<p>hi</p>"


@respx.mock
async def test_aclose_leaves_shared_client_open(client: httpx.AsyncClient) -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, headers={"content-type": "text/html"}))
    fetcher = SharedClientFetcher(client)
    await fetcher.aclose()
    assert not client.is_closed
    # A second crawl's fetcher can still use the same client.
    assert (await SharedClientFetcher(client).fetch(URL)).status == 200


async def test_job_writer_records_pages_and_distinct_links() -> None:
    job = CrawlJob(id="j", config=CrawlConfig(URL))
    writer = JobWriter(job)
    home = PageResult(URL, (f"{URL}a", f"{URL}b"))
    page_a = PageResult(f"{URL}a", (f"{URL}b", f"{URL}c"))
    await writer.write(home)
    await writer.write(page_a)
    await writer.aclose()

    assert job.pages == [home, page_a]
    assert job.links == [f"{URL}a", f"{URL}b", f"{URL}c"]
    assert job.link_set == set(job.links)
