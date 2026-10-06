"""End-to-end integration test over a real local HTTP server.

Unlike the unit tests (which mock individual responses), this drives the real
HttpxFetcher, LinkExtractor and Crawler against an actual TCP server serving a
known link-graph, so the whole stack is exercised over real HTTP: cycles, a
redirect, a non-HTML resource, a 404 and an off-domain link.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urljoin

import pytest

from crawler.crawler import Crawler
from crawler.extractor import LinkExtractor
from crawler.fetcher import HttpxFetcher

# path -> (kind, payload). kind drives the response the handler produces.
SITE: dict[str, tuple[str, str]] = {
    "/": (
        "html",
        '<a href="/a">a</a><a href="/b">b</a><a href="/old">old</a>'
        '<a href="/file.pdf">pdf</a><a href="/missing">missing</a>'
        '<a href="#section">frag</a><a href="http://external.test/x">ext</a>',
    ),
    "/a": ("html", '<a href="/b">b</a><a href="/">home</a>'),  # cycle back home
    "/b": ("html", '<a href="/a">a</a><a href="/c">c</a>'),  # cycle a<->b
    "/c": ("html", "<p>leaf</p>"),
    "/old": ("redirect", "/new"),
    "/new": ("html", '<a href="/c">c</a>'),  # relative link resolves against /new
    "/file.pdf": ("pdf", ""),
    "/missing": ("notfound", ""),
}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # silence test noise
        pass

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        spec = SITE.get(path)
        if spec is None:
            self._send(404, "text/html", b"not found")
            return
        kind, payload = spec
        if kind == "html":
            self._send(200, "text/html", payload.encode())
        elif kind == "pdf":
            self._send(200, "application/pdf", b"%PDF-1.7 fake")
        elif kind == "notfound":
            self._send(404, "text/html", b"nope")
        elif kind == "redirect":
            self.send_response(301)
            self.send_header("Location", payload)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def site() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/"
    finally:
        server.shutdown()
        thread.join()


async def _crawl(base_url: str, **kwargs: object) -> list:  # type: ignore[type-arg]
    async with HttpxFetcher(timeout=5.0) as fetcher:
        crawler = Crawler(fetcher, LinkExtractor(), base_url=base_url, **kwargs)  # type: ignore[arg-type]
        return [page async for page in crawler.crawl()]


async def test_full_crawl_over_real_http(site: str) -> None:
    pages = await _crawl(site)
    by_url = {p.url: p for p in pages}

    def u(path: str) -> str:
        return urljoin(site, path)

    # Every reachable same-site page is visited exactly once; cycles terminate.
    assert set(by_url) == {
        site,
        u("/a"),
        u("/b"),
        u("/c"),
        u("/old"),
        u("/file.pdf"),
        u("/missing"),
    }
    assert len(pages) == len(by_url)  # no page emitted twice

    # Off-domain link: reported on the home page but never fetched.
    assert "http://external.test/x" in by_url[site].links
    assert not any(p.url.startswith("http://external.test") for p in pages)

    # A 404 is reported, not fatal.
    assert by_url[u("/missing")].status_code == 404

    # Non-HTML resource: fetched, reported, but not mined for links.
    assert by_url[u("/file.pdf")].links == ()

    # Redirect: /new is reached only via /old's redirect (not a page of its own),
    # and /old's relative link resolves against the post-redirect URL.
    assert u("/new") not in by_url
    assert u("/c") in by_url[u("/old")].links


async def test_max_pages_limit_over_real_http(site: str) -> None:
    pages = await _crawl(site, max_pages=3)
    by_url = {p.url: p for p in pages}

    assert site in by_url
    assert len(pages) == 3
