import asyncio
from typing import Dict, Optional

from site_crawler.fetcher import Fetcher


class _FakeResponse:
    def __init__(self, status: int, headers: Dict[str, str], text_value: str = "") -> None:
        self.status = status
        self.headers = headers
        self._text = text_value

    async def text(self, errors: Optional[str] = None) -> str:
        # mimic aiohttp.TextResponse.text signature enough for our use
        return self._text


class _FakeContext:
    def __init__(self, resp: _FakeResponse):
        self._resp = resp

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, resp: _FakeResponse):
        self._resp = resp

    def get(self, url: str, allow_redirects: bool = True):
        # return an async context manager directly (not a coroutine)
        return _FakeContext(self._resp)


class _FakeSessionRaise:
    def get(self, url: str, allow_redirects: bool = True):
        raise RuntimeError("network error")


import pytest


@pytest.mark.parametrize(
    "status,headers,text,raise_exc,expected",
    [
        (200, {"Content-Type": "text/html; charset=utf-8"}, "<html>ok</html>", False, "<html>ok</html>"),
        (200, {"Content-Type": "application/json"}, "{}", False, None),
        (404, {"Content-Type": "text/html"}, "Not Found", False, None),
        (None, None, None, True, None),
    ],
)
def test_fetcher_fetch_parametrized(status, headers, text, raise_exc, expected):
    fetcher = Fetcher()
    if raise_exc:
        session = _FakeSessionRaise()
    else:
        resp = _FakeResponse(status, headers or {}, text or "")
        session = _FakeSession(resp)

    result = asyncio.run(fetcher.fetch(session, "https://example.com/"))
    assert result == expected
