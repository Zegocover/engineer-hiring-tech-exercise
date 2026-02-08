from __future__ import annotations

import pytest
from aiohttp import web

from crawler.page_worker import PageWorker


@pytest.mark.asyncio
async def test_page_worker_extracts_same_domain_links() -> None:
    app = web.Application()

    async def index(request: web.Request) -> web.Response:
        return web.Response(
            text="""
            <html>
              <body>
                <a href="/page">Page</a>
                <a href="/page#fragment">Page Fragment</a>
                <a href="https://example.com/">External</a>
                <a href="mailto:test@example.com">Mail</a>
              </body>
            </html>
            """,
            content_type="text/html",
        )

    async def page(request: web.Request) -> web.Response:
        return web.Response(text="<html>ok</html>", content_type="text/html")

    app.router.add_get("/", index)
    app.router.add_get("/page", page)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()

    try:
        port = site._server.sockets[0].getsockname()[1]
        base_url = f"http://127.0.0.1:{port}/"
        page_url = f"http://127.0.0.1:{port}/page"

        worker = PageWorker(base_url=base_url)
        result = await worker.fetch(base_url)

        assert result.crawlable_links == [page_url]
        assert set(result.links) == {page_url, "https://example.com/"}
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_page_worker_non_html_returns_no_links() -> None:
    app = web.Application()

    async def index(request: web.Request) -> web.Response:
        return web.Response(text="plain", content_type="text/plain")

    app.router.add_get("/", index)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()

    try:
        port = site._server.sockets[0].getsockname()[1]
        base_url = f"http://127.0.0.1:{port}/"
        worker = PageWorker(base_url=base_url)
        result = await worker.fetch(base_url)

        assert result.links == []
        assert result.crawlable_links == []
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_page_worker_invalid_url_sets_error() -> None:
    worker = PageWorker(base_url="https://example.com")
    result = await worker.fetch("http://")

    assert result.error
    assert result.links == []
    assert result.crawlable_links == []
