from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest
import respx

from crawler.src.fetcher import Fetcher


def _html(text: str = "ok") -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "text/html"}, text=text)


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
            fetcher = Fetcher(client, max_retries=0)
            result = await fetcher.fetch("https://example.com/page")

    assert result.status == 200
    assert result.html == "<html></html>"
    assert result.error is None


@pytest.mark.asyncio
async def test_fetch_retries_then_succeeds():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/flaky")
            route.side_effect = [httpx.Response(503), _html()]
            fetcher = Fetcher(client, max_retries=2, backoff_base=0.01, backoff_cap=0.02)
            result = await fetcher.fetch("https://example.com/flaky")

    assert result.html == "ok"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_fetch_exhausts_retries_and_fails():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/down").mock(return_value=httpx.Response(503))
            fetcher = Fetcher(client, max_retries=2, backoff_base=0.01, backoff_cap=0.02)
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
            fetcher = Fetcher(client, max_retries=0)
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
            fetcher = Fetcher(client, max_retries=0)
            result = await fetcher.fetch("https://example.com/old")

    assert result.url == "https://example.com/new"
    assert result.html == "new page"


@pytest.mark.asyncio
async def test_fetch_non_200_non_retryable_status_returns_no_html():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/missing").mock(return_value=httpx.Response(404))
            fetcher = Fetcher(client, max_retries=2)
            result = await fetcher.fetch("https://example.com/missing")

    assert result.status == 404
    assert result.html is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
async def test_retries_on_each_retryable_status(status):
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/flaky")
            route.side_effect = [httpx.Response(status), _html()]
            fetcher = Fetcher(client, max_retries=1, backoff_base=0.01, backoff_cap=0.02)
            result = await fetcher.fetch("https://example.com/flaky")

    assert result.html == "ok"
    assert route.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [501, 505])
async def test_does_not_retry_permanent_server_errors(status):
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/broken").mock(return_value=httpx.Response(status))
            fetcher = Fetcher(client, max_retries=3, backoff_base=0.01, backoff_cap=0.02)
            result = await fetcher.fetch("https://example.com/broken")

    assert result.status == status
    assert result.html is None
    assert route.call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 403, 404])
async def test_does_not_retry_generic_client_errors(status):
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/bad").mock(return_value=httpx.Response(status))
            fetcher = Fetcher(client, max_retries=3)
            result = await fetcher.fetch("https://example.com/bad")

    assert result.status == status
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_retries_on_timeout_exception():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/slow")
            route.side_effect = [httpx.TimeoutException("timed out"), _html()]
            fetcher = Fetcher(client, max_retries=1, backoff_base=0.01, backoff_cap=0.02)
            result = await fetcher.fetch("https://example.com/slow")

    assert result.html == "ok"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_retries_on_transport_error():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/unreachable")
            route.side_effect = [httpx.ConnectError("boom"), _html()]
            fetcher = Fetcher(client, max_retries=1, backoff_base=0.01, backoff_cap=0.02)
            result = await fetcher.fetch("https://example.com/unreachable")

    assert result.html == "ok"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_exhausts_retries_reports_last_exception_message():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/dead")
            route.side_effect = [
                httpx.TimeoutException("boom 1"),
                httpx.TimeoutException("boom 2"),
            ]
            fetcher = Fetcher(client, max_retries=1, backoff_base=0.01, backoff_cap=0.02)
            result = await fetcher.fetch("https://example.com/dead")

    assert result.html is None
    assert result.status is None
    assert "boom 2" in (result.error or "")
    assert route.call_count == 2

@pytest.mark.asyncio
async def test_backoff_delay_grows_exponentially(monkeypatch):
    sleeps = _record_sleeps(monkeypatch)
    monkeypatch.setattr("crawler.src.fetcher.random.uniform", lambda a, b: 0.0)

    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/flaky")
            # 500s (not 429/503) so the adaptive throttle never contributes a sleep call here.
            route.side_effect = [
                httpx.Response(500),
                httpx.Response(500),
                httpx.Response(500),
                _html(),
            ]
            fetcher = Fetcher(client, max_retries=3, backoff_base=1.0, backoff_cap=100.0)
            result = await fetcher.fetch("https://example.com/flaky")

    assert result.html == "ok"
    assert sleeps == [1.0, 2.0, 4.0]


@pytest.mark.asyncio
async def test_backoff_delay_capped_at_backoff_cap(monkeypatch):
    sleeps = _record_sleeps(monkeypatch)
    monkeypatch.setattr("crawler.src.fetcher.random.uniform", lambda a, b: 0.0)

    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/flaky")
            route.side_effect = [httpx.Response(500)] * 5 + [_html()]
            fetcher = Fetcher(client, max_retries=5, backoff_base=1.0, backoff_cap=3.0)
            result = await fetcher.fetch("https://example.com/flaky")

    assert result.html == "ok"
    assert sleeps == [1.0, 2.0, 3.0, 3.0, 3.0]


@pytest.mark.asyncio
async def test_backoff_includes_jitter(monkeypatch):
    sleeps = _record_sleeps(monkeypatch)
    monkeypatch.setattr("crawler.src.fetcher.random.uniform", lambda low, high: high)

    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/flaky")
            route.side_effect = [httpx.Response(500), _html()]
            fetcher = Fetcher(client, max_retries=1, backoff_base=1.0, backoff_cap=100.0)
            result = await fetcher.fetch("https://example.com/flaky")

    assert result.html == "ok"
    assert sleeps == [pytest.approx(1.1)]


@pytest.mark.asyncio
async def test_retry_after_seconds_used_as_backoff_delay(monkeypatch):
    sleeps = _record_sleeps(monkeypatch)

    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/limited")
            route.side_effect = [
                httpx.Response(500, headers={"retry-after": "2"}),
                _html(),
            ]
            fetcher = Fetcher(client, max_retries=1, backoff_base=0.01, backoff_cap=10.0)
            result = await fetcher.fetch("https://example.com/limited")

    assert result.html == "ok"
    assert sleeps == [2.0]


@pytest.mark.asyncio
async def test_retry_after_http_date_used_as_backoff_delay(monkeypatch):
    sleeps = _record_sleeps(monkeypatch)

    # We pin what "now" represents
    fixed_now = datetime(2024, 1, 1, tzinfo=UTC)
    retry_at = fixed_now + timedelta(seconds=3)

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr("crawler.src.fetcher.datetime", _FixedDatetime)

    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/limited")
            route.side_effect = [
                httpx.Response(
                    500, headers={"retry-after": format_datetime(retry_at, usegmt=True)}
                ),
                _html(),
            ]
            fetcher = Fetcher(client, max_retries=1, backoff_base=0.01, backoff_cap=10.0)
            result = await fetcher.fetch("https://example.com/limited")

    assert result.html == "ok"
    assert sleeps == [pytest.approx(3.0)]


@pytest.mark.asyncio
async def test_retry_after_capped_at_backoff_cap(monkeypatch):
    sleeps = _record_sleeps(monkeypatch)

    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/limited")
            route.side_effect = [
                httpx.Response(500, headers={"retry-after": "300"}),
                _html(),
            ]
            fetcher = Fetcher(client, max_retries=1, backoff_base=0.01, backoff_cap=5.0)
            result = await fetcher.fetch("https://example.com/limited")

    assert result.html == "ok"
    assert sleeps == [5.0]


@pytest.mark.asyncio
async def test_missing_retry_after_falls_back_to_exponential_backoff(monkeypatch):
    sleeps = _record_sleeps(monkeypatch)
    monkeypatch.setattr("crawler.src.fetcher.random.uniform", lambda a, b: 0.0)

    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/flaky")
            route.side_effect = [httpx.Response(500), _html()]  # no retry-after header
            fetcher = Fetcher(client, max_retries=1, backoff_base=2.0, backoff_cap=10.0)
            result = await fetcher.fetch("https://example.com/flaky")

    assert result.html == "ok"
    assert sleeps == [2.0]


@pytest.mark.asyncio
async def test_malformed_retry_after_falls_back_to_exponential_backoff(monkeypatch):
    sleeps = _record_sleeps(monkeypatch)
    monkeypatch.setattr("crawler.src.fetcher.random.uniform", lambda a, b: 0.0)

    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/flaky")
            route.side_effect = [
                httpx.Response(500, headers={"retry-after": "not-a-valid-value"}),
                _html(),
            ]
            fetcher = Fetcher(client, max_retries=1, backoff_base=2.0, backoff_cap=10.0)
            result = await fetcher.fetch("https://example.com/flaky")

    assert result.html == "ok"
    assert sleeps == [2.0]


@pytest.mark.asyncio
async def test_min_delay_sleeps_before_every_attempt(monkeypatch):
    sleeps = _record_sleeps(monkeypatch)

    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/flaky")
            route.side_effect = [httpx.Response(503), _html()]
            fetcher = Fetcher(
                client, max_retries=1, backoff_base=0.0, backoff_cap=0.0, min_delay=0.3
            )
            result = await fetcher.fetch("https://example.com/flaky")

    assert result.html == "ok"
    # One sleep(0.3) before each of the two attempts, plus the (zeroed-out) backoff sleep
    # in between.
    assert sleeps.count(pytest.approx(0.3)) == 2


@pytest.mark.asyncio
async def test_zero_min_delay_never_sleeps_for_pacing():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/page").mock(return_value=_html())
            fetcher = Fetcher(client, max_retries=0, min_delay=0.0)
            result = await fetcher.fetch("https://example.com/page")

    assert result.html == "ok"
