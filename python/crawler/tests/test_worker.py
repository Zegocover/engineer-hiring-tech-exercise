from __future__ import annotations

import aiohttp
import pytest
from aiohttp import web

from crawler.worker import Worker


@pytest.mark.asyncio
async def test_worker_extracts_same_domain_links() -> None:
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

        async with aiohttp.ClientSession() as session:
            worker = Worker(base_url=base_url, session=session)
            result = await worker.fetch(base_url)

        assert result.crawlable_links == [page_url]
        assert set(result.links) == {page_url, "https://example.com/"}
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_worker_non_html_returns_no_links() -> None:
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
        async with aiohttp.ClientSession() as session:
            worker = Worker(base_url=base_url, session=session)
            result = await worker.fetch(base_url)

        assert result.links == []
        assert result.crawlable_links == []
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_worker_invalid_url_sets_error() -> None:
    async with aiohttp.ClientSession() as session:
        worker = Worker(base_url="https://example.com", session=session)
        result = await worker.fetch("http://")

    assert result.error
    assert result.links == []
    assert result.crawlable_links == []


@pytest.mark.asyncio
async def test_worker_redirect_to_external_domain_sets_error() -> None:
    app = web.Application()
    external_app = web.Application()

    async def redirect(request: web.Request) -> web.Response:
        return web.HTTPFound(location=external_url)

    async def external(request: web.Request) -> web.Response:
        return web.Response(text="<html>external</html>", content_type="text/html")

    external_app.router.add_get("/", external)

    external_runner = web.AppRunner(external_app)
    await external_runner.setup()
    external_site = web.TCPSite(external_runner, "127.0.0.1", 0)
    await external_site.start()

    try:
        external_port = external_site._server.sockets[0].getsockname()[1]
        external_url = f"http://127.0.0.1:{external_port}/"
        app.router.add_get("/", redirect)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()

        try:
            port = site._server.sockets[0].getsockname()[1]
            base_url = f"http://127.0.0.1:{port}/"
            async with aiohttp.ClientSession() as session:
                worker = Worker(base_url=base_url, session=session)
                result = await worker.fetch(base_url)

            assert result.error == "redirected to external domain"
            assert result.links == []
            assert result.crawlable_links == []
        finally:
            await runner.cleanup()
    finally:
        await external_runner.cleanup()
