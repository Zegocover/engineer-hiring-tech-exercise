"""Local sites for crawler tests. No requests leave the machine."""

import pytest
from aiohttp import web


@pytest.fixture
async def serve():
    """Start an in-process site from ``(path, body, status)`` routes."""
    runners = []

    async def _serve(routes):
        app = web.Application()
        for path, body, status in routes:
            async def handler(_request, body=body, status=status):
                if status >= 400:
                    return web.Response(status=status, text=body or "error")
                return web.Response(text=body, content_type="text/html")

            app.router.add_get(path, handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        runners.append(runner)
        port = site._server.sockets[0].getsockname()[1]
        return "http://127.0.0.1:%s/" % port

    yield _serve
    for runner in runners:
        await runner.cleanup()
