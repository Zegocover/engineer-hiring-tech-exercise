import httpx
import pytest

from site_crawler.parser import (
    ExternalRedirectError,
    NonHtmlContentError,
    extract_links,
    extract_links_from_url_async,
)
from site_crawler.url_policy import UrlPolicy


class FakeResponse:
    status_code = 200
    text = '<a href="/docs">Docs</a>'
    headers = {"content-type": "text/html; charset=utf-8"}

    def raise_for_status(self) -> None:
        pass


class NoLinksResponse:
    status_code = 200
    text = "<html><body><p>No links here.</p></body></html>"
    headers = {"content-type": "text/html"}

    def raise_for_status(self) -> None:
        pass


class FakeAsyncClient:
    def __init__(self, responses: list[object]) -> None:
        self._responses = iter(responses)
        self.requested_urls: list[str] = []

    async def get(
        self, url: str, headers: dict, timeout: float
    ) -> object:
        self.requested_urls.append(url)
        return next(self._responses)


def test_extract_links_resolves_relative_urls_and_drops_fragments() -> None:
    html = (
        '<a href="/docs#intro">Docs</a><a href="https://other.test">Other</a>'
    )

    assert extract_links(html, "https://example.test/start") == (
        "https://example.test/docs",
        "https://other.test/",
    )


def test_extract_links_can_include_duplicates() -> None:
    html = '<a href="/docs">One</a><a href="/docs">Two</a>'

    assert extract_links(html, "https://example.test", True) == (
        "https://example.test/docs",
        "https://example.test/docs",
    )


@pytest.mark.asyncio
async def test_extract_links_from_url_fetches_and_parses_page() -> None:
    client = FakeAsyncClient([FakeResponse()])

    assert await extract_links_from_url_async(
        client, "https://example.test/start"
    ) == [
        "https://example.test/docs"
    ]


@pytest.mark.asyncio
async def test_extract_links_from_url_returns_no_links():
    client = FakeAsyncClient([NoLinksResponse()])

    assert await extract_links_from_url_async(
        client, "https://example.test"
    ) == []


@pytest.mark.asyncio
async def test_extract_links_from_url_rejects_non_html_content() -> None:
    class PdfResponse:
        status_code = 200
        headers = {"content-type": "application/pdf"}
        text = "not html"

        def raise_for_status(self) -> None:
            pass

    with pytest.raises(NonHtmlContentError, match="application/pdf"):
        await extract_links_from_url_async(
            FakeAsyncClient([PdfResponse()]),
            "https://example.test/document.pdf",
        )


@pytest.mark.asyncio
async def test_extract_links_from_url_rejects_external_redirect() -> None:
    request = httpx.Request("GET", "https://example.test")
    redirect = httpx.Response(
        302,
        headers={"Location": "https://other.test/"},
        request=request,
    )
    client = FakeAsyncClient([redirect])

    with pytest.raises(ExternalRedirectError, match="outside original host"):
        await extract_links_from_url_async(
            client,
            "https://example.test",
            url_policy=UrlPolicy("https://example.test"),
        )

    assert client.requested_urls == ["https://example.test"]


@pytest.mark.asyncio
async def test_extract_links_from_url_uses_retry_after_for_rate_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request("GET", "https://example.test")
    rate_limited_response = httpx.Response(
        429,
        headers={"Retry-After": "3"},
        request=request,
    )
    successful_response = FakeResponse()
    wait_times: list[float] = []

    async def record_sleep(delay: float) -> None:
        wait_times.append(delay)

    monkeypatch.setattr("site_crawler.parser.asyncio.sleep", record_sleep)

    assert await extract_links_from_url_async(
        FakeAsyncClient([rate_limited_response, successful_response]),
        "https://example.test",
    ) == [
        "https://example.test/docs"
    ]
    assert wait_times == [3.0]


@pytest.mark.asyncio
async def test_extract_links_from_url_raises_after_three_rate_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request("GET", "https://example.test")
    rate_limited_response = httpx.Response(429, request=request)
    wait_times: list[float] = []

    async def record_sleep(delay: float) -> None:
        wait_times.append(delay)

    monkeypatch.setattr("site_crawler.parser.asyncio.sleep", record_sleep)

    with pytest.raises(httpx.HTTPStatusError):
        await extract_links_from_url_async(
            FakeAsyncClient(
                [
                    rate_limited_response,
                    rate_limited_response,
                    rate_limited_response,
                ]
            ),
            "https://example.test",
        )

    assert wait_times == [1.0, 2.0]
