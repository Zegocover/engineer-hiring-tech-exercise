import httpx
import pytest
import respx
from httpx_retries import Retry, RetryTransport

from crawler.src.fetcher import Fetcher

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _html(text: str = "ok") -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "text/html"}, text=text)


def _retrying_client(
    *,
    total: int,
    status_forcelist: set[int] | None = None,
    backoff_factor: float = 0.01,
    max_backoff_wait: float = 0.02,
) -> httpx.AsyncClient:
    """A client whose transport retries like the one crawler.src.cli builds, but with
    tiny backoff so tests stay fast. Fetcher itself no longer retries at all -- that's
    delegated entirely to this transport (see httpx-retries).
    """
    retry = Retry(
        total=total,
        status_forcelist=_RETRYABLE_STATUS if status_forcelist is None else status_forcelist,
        backoff_factor=backoff_factor,
        max_backoff_wait=max_backoff_wait,
    )
    return httpx.AsyncClient(transport=RetryTransport(retry=retry))


def _record_sleeps(monkeypatch) -> list[float]:
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("crawler.src.fetcher.asyncio.sleep", fake_sleep)
    return sleeps


@pytest.mark.asyncio
async def test_fetch_success_returns_html():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/page").mock(return_value=_html("<html></html>"))
            fetcher = Fetcher(client)
            result = await fetcher.fetch("https://example.com/page")

    assert result.status == 200
    assert result.html == "<html></html>"
    assert result.error is None


@pytest.mark.asyncio
async def test_fetch_retries_then_succeeds():
    async with _retrying_client(total=2) as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/flaky")
            route.side_effect = [httpx.Response(503), _html()]
            fetcher = Fetcher(client)
            result = await fetcher.fetch("https://example.com/flaky")

    assert result.html == "ok"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_fetch_exhausts_retries_and_fails():
    async with _retrying_client(total=2) as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/down").mock(return_value=httpx.Response(503))
            fetcher = Fetcher(client)
            result = await fetcher.fetch("https://example.com/down")

    assert result.html is None
    assert result.error is not None
    assert route.call_count == 3  # initial attempt + 2 retries


@pytest.mark.asyncio
async def test_fetch_skips_non_html_content_type():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/file.pdf").mock(
                return_value=httpx.Response(
                    200, headers={"content-type": "application/pdf"}, content=b"%PDF"
                )
            )
            fetcher = Fetcher(client)
            result = await fetcher.fetch("https://example.com/file.pdf")

    assert result.html is None
    assert "content-type" in (result.error or "")


@pytest.mark.asyncio
async def test_fetch_reports_final_url_after_redirect():
    async with httpx.AsyncClient(follow_redirects=True) as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/old").mock(
                return_value=httpx.Response(301, headers={"location": "https://example.com/new"})
            )
            mock.get("/new").mock(return_value=_html("new page"))
            fetcher = Fetcher(client)
            result = await fetcher.fetch("https://example.com/old")

    assert result.url == "https://example.com/new"
    assert result.html == "new page"


@pytest.mark.asyncio
async def test_fetch_non_200_non_retryable_status_returns_no_html():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/missing").mock(return_value=httpx.Response(404))
            fetcher = Fetcher(client)
            result = await fetcher.fetch("https://example.com/missing")

    assert result.status == 404
    assert result.html is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
async def test_retries_on_each_retryable_status(status):
    async with _retrying_client(total=1) as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/flaky")
            route.side_effect = [httpx.Response(status), _html()]
            fetcher = Fetcher(client)
            result = await fetcher.fetch("https://example.com/flaky")

    assert result.html == "ok"
    assert route.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [501, 505])
async def test_does_not_retry_permanent_server_errors(status):
    async with _retrying_client(total=3) as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/broken").mock(return_value=httpx.Response(status))
            fetcher = Fetcher(client)
            result = await fetcher.fetch("https://example.com/broken")

    assert result.status == status
    assert result.html is None
    assert route.call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 403, 404])
async def test_does_not_retry_generic_client_errors(status):
    async with _retrying_client(total=3) as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/bad").mock(return_value=httpx.Response(status))
            fetcher = Fetcher(client)
            result = await fetcher.fetch("https://example.com/bad")

    assert result.status == status
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_retries_on_timeout_exception():
    async with _retrying_client(total=1) as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/slow")
            route.side_effect = [httpx.TimeoutException("timed out"), _html()]
            fetcher = Fetcher(client)
            result = await fetcher.fetch("https://example.com/slow")

    assert result.html == "ok"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_retries_on_transport_error():
    async with _retrying_client(total=1) as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/unreachable")
            route.side_effect = [httpx.ConnectError("boom"), _html()]
            fetcher = Fetcher(client)
            result = await fetcher.fetch("https://example.com/unreachable")

    assert result.html == "ok"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_exhausts_retries_reports_last_exception_message():
    async with _retrying_client(total=1) as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/dead")
            route.side_effect = [
                httpx.TimeoutException("boom 1"),
                httpx.TimeoutException("boom 2"),
            ]
            fetcher = Fetcher(client)
            result = await fetcher.fetch("https://example.com/dead")

    assert result.html is None
    assert result.status is None
    assert "boom 2" in (result.error or "")
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_retry_after_header_is_respected(monkeypatch):
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("httpx_retries.retry.asyncio.sleep", fake_sleep)

    async with _retrying_client(total=1, max_backoff_wait=10.0) as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/limited")
            route.side_effect = [
                httpx.Response(503, headers={"retry-after": "2"}),
                _html(),
            ]
            fetcher = Fetcher(client)
            result = await fetcher.fetch("https://example.com/limited")

    assert result.html == "ok"
    assert route.call_count == 2
    assert sleeps == [pytest.approx(2.0)]


@pytest.mark.asyncio
async def test_min_delay_sleeps_once_before_fetch(monkeypatch):
    sleeps = _record_sleeps(monkeypatch)

    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/page").mock(return_value=_html())
            fetcher = Fetcher(client, min_delay=0.3)
            result = await fetcher.fetch("https://example.com/page")

    assert result.html == "ok"
    assert sleeps == [pytest.approx(0.3)]


@pytest.mark.asyncio
async def test_zero_min_delay_never_sleeps_for_pacing():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/page").mock(return_value=_html())
            fetcher = Fetcher(client, min_delay=0.0)
            result = await fetcher.fetch("https://example.com/page")

    assert result.html == "ok"
