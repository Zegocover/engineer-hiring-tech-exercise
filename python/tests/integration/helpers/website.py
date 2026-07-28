import asyncio
import time
from dataclasses import dataclass, field

from fastapi import FastAPI, Request, Response


@dataclass
class Page:
    body: str = ""
    status: int = 200
    content_type: str = "text/html"
    headers: dict[str, str] = field(default_factory=dict)
    delay: float = 0.0
    size: int | None = None  # if set, emit this many bytes instead of body
    omit_content_type: bool = False


def make_app(pages: dict[str, Page]) -> tuple[FastAPI, list[tuple[str, str, float]]]:
    """Builds a dummy site from a page spec table plus a request recorder."""
    app = FastAPI()
    requests: list[tuple[str, str, float]] = []

    @app.middleware("http")
    async def record_requests(request: Request, call_next):
        requests.append((request.method, request.url.path, time.monotonic()))
        return await call_next(request)

    @app.get("/{path:path}")
    async def serve(path: str):
        spec = pages.get("/" + path.lstrip("/"))
        if spec is None:
            return Response(status_code=404)
        if spec.delay:
            await asyncio.sleep(spec.delay)
        content = b"\0" * spec.size if spec.size else spec.body.encode()
        if spec.omit_content_type:
            return Response(
                content=content, status_code=spec.status, headers=dict(spec.headers)
            )
        return Response(
            content=content,
            status_code=spec.status,
            headers=dict(spec.headers),
            media_type=spec.content_type,
        )

    return app, requests
