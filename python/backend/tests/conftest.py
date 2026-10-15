from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import httpx
import pytest
from site_crawler.interfaces import Fetcher

from crawler_api.main import create_app
from crawler_api.settings import Settings
from tests.fakes import FakeSite

ApiOpener = Callable[..., AbstractAsyncContextManager[httpx.AsyncClient]]


@asynccontextmanager
async def open_api(
    fetcher: Fetcher | Callable[[], Fetcher], settings: Settings | None = None
) -> AsyncIterator[httpx.AsyncClient]:
    """Run the real app, lifespan included, with ``fetcher`` serving every crawl.

    Pass a fetcher to share it across crawls, or a factory for one per crawl.
    """
    factory = fetcher if callable(fetcher) else (lambda: fetcher)
    app = create_app(settings or Settings(), factory)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client,
    ):
        yield client


@pytest.fixture
def api() -> ApiOpener:
    return open_api


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with open_api(FakeSite({})) as c:
        yield c
