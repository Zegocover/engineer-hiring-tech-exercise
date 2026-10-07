"""Application factory: wires settings, the shared HTTP client and the service.

Run with ``uv run uvicorn crawler_api.main:app``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from site_crawler.models import ConfigError

from crawler_api.adapters import SharedClientFetcher
from crawler_api.routes import router
from crawler_api.service import CrawlService, FetcherFactory, LimitError
from crawler_api.settings import Settings


def create_app(
    settings: Settings | None = None,
    fetcher_factory: FetcherFactory | None = None,
) -> FastAPI:
    """Build the app.

    ``fetcher_factory`` makes one fetcher per crawl. By default every crawl
    gets a :class:`SharedClientFetcher` over one client owned by the app;
    tests pass in-memory fetchers instead.
    """
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client: httpx.AsyncClient | None = None
        factory = fetcher_factory
        if factory is None:
            shared = client = _shared_client(settings)
            factory = lambda: SharedClientFetcher(shared)  # noqa: E731
        service = CrawlService(settings, factory)
        app.state.service = service
        try:
            yield
        finally:
            # Crawls must stop before the client they share is closed.
            await service.shutdown()
            if client is not None:
                await client.aclose()

    app = FastAPI(
        title="Crawler API",
        summary="Start, monitor and cancel single-host site crawls.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    app.add_exception_handler(ConfigError, _invalid_request)
    app.add_exception_handler(LimitError, _invalid_request)

    @app.get("/health", tags=["service"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _shared_client(settings: Settings) -> httpx.AsyncClient:
    """The one HTTP client every crawl fetches through."""
    return httpx.AsyncClient(
        follow_redirects=True,
        # pool=None: under load, wait for a free connection instead of failing.
        timeout=httpx.Timeout(settings.request_timeout, pool=None),
        limits=httpx.Limits(
            max_connections=settings.max_connections,
            max_keepalive_connections=settings.max_connections,
        ),
        headers={"User-Agent": settings.user_agent},
    )


async def _invalid_request(request: Request, exc: Exception) -> JSONResponse:
    """Report a request the crawler or the service limits rejected.

    Uses the same body shape FastAPI uses for its own validation errors.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": [{"type": "value_error", "loc": ["body"], "msg": str(exc)}]},
    )


app = create_app()
