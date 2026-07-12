import httpx
import pytest
import respx

from crawler.src.fetcher import Fetcher


@pytest.mark.asyncio
async def test_fetch_success_returns_html() -> None:
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/page").mock(
                return_value=httpx.Response(
                    200, headers={"content-type": "text/html"}, text="<html></html>"
                )
            )
            fetcher = Fetcher(client, max_retries=0)
            result = await fetcher.fetch("https://example.com/page")

    assert result.status == 200
    assert result.html == "<html></html>"
    assert result.error is None


@pytest.mark.asyncio
async def test_fetch_retries_then_succeeds() -> None:
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/flaky")
            route.side_effect = [
                httpx.Response(503),
                httpx.Response(200, headers={"content-type": "text/html"}, text="ok"),
            ]
            fetcher = Fetcher(client, max_retries=2, backoff_base=0.01, backoff_cap=0.02)
            result = await fetcher.fetch("https://example.com/flaky")

    assert result.html == "ok"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_fetch_exhausts_retries_and_fails() -> None:
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/down").mock(return_value=httpx.Response(503))
            fetcher = Fetcher(client, max_retries=2, backoff_base=0.01, backoff_cap=0.02)
            result = await fetcher.fetch("https://example.com/down")

    assert result.html is None
    assert result.error is not None
    assert route.call_count == 3  # initial attempt + 2 retries


@pytest.mark.asyncio
async def test_fetch_skips_non_html_content_type() -> None:
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/file.pdf").mock(
                return_value=httpx.Response(
                    200, headers={"content-type": "application/pdf"}, content=b"%PDF"
                )
            )
            fetcher = Fetcher(client, max_retries=0)
            result = await fetcher.fetch("https://example.com/file.pdf")

    assert result.html is None
    assert "content-type" in (result.error or "")


@pytest.mark.asyncio
async def test_fetch_reports_final_url_after_redirect() -> None:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/old").mock(
                return_value=httpx.Response(301, headers={"location": "https://example.com/new"})
            )
            mock.get("/new").mock(
                return_value=httpx.Response(
                    200, headers={"content-type": "text/html"}, text="new page"
                )
            )
            fetcher = Fetcher(client, max_retries=0)
            result = await fetcher.fetch("https://example.com/old")

    assert result.url == "https://example.com/new"
    assert result.html == "new page"


@pytest.mark.asyncio
async def test_fetch_non_200_non_retryable_status_returns_no_html() -> None:
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/missing").mock(return_value=httpx.Response(404))
            fetcher = Fetcher(client, max_retries=2)
            result = await fetcher.fetch("https://example.com/missing")

    assert result.status == 404
    assert result.html is None
