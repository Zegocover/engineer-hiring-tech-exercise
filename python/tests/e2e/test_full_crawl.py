"""End-to-end crawl over on-disk HTML fixtures, driven through the real stack.

A richer companion to ``test_smoke.py``. A small multi-page site
(``tests/e2e/sites/acme``) exercises every behaviour the brief cares about:
same-host following, subdomain *and* offsite "list but don't follow", URL
normalization (relative, fragment, duplicate, non-http schemes), a cycle back to
the seed, an HTTP 404, and a transport failure. The httpx client is mocked
file-by-path, so every real component (``HttpxFetcher``, ``SelectolaxExtractor``,
the engine) runs unchanged — only the network is faked.
"""

import json
from pathlib import Path

import httpx
import pytest
from pytest_httpx import HTTPXMock

from crawler.factory import crawler_factory
from crawler.presenters import format_jsonl, format_text
from domains.crawler.models import CrawlConfig, PageResult

SITES = Path(__file__).parent / "sites"
BASE = "https://acme.test/"
HOST = "acme.test"


def _register_site(httpx_mock: HTTPXMock, base_url: str, site: str) -> None:
    """Serve every ``*.html`` under ``sites/<site>`` by URL path.

    ``index.html`` maps to the base URL itself; ``about.html`` to ``base + about``.
    """
    for path in sorted((SITES / site).glob("*.html")):
        slug = "" if path.stem == "index" else path.stem
        httpx_mock.add_response(
            url=f"{base_url}{slug}",
            html=path.read_text(),
            headers={"content-type": "text/html"},
        )


@pytest.fixture
def acme_site(httpx_mock: HTTPXMock) -> None:
    """Wire up the acme.test fixture site plus its two failing on-host links."""
    _register_site(httpx_mock, BASE, "acme")
    httpx_mock.add_response(url=f"{BASE}missing", status_code=404)
    httpx_mock.add_exception(httpx.ConnectError("connection refused"), url=f"{BASE}broken")


async def _crawl(config: CrawlConfig) -> tuple[dict[str, PageResult], bool]:
    """Run a full crawl and collect the pages keyed by URL, plus the truncated flag."""
    pages: dict[str, PageResult] = {}
    async with httpx.AsyncClient() as client:
        crawler = crawler_factory(config, client)
        async for page in crawler.crawl():
            pages[page.url] = page
        return pages, crawler.truncated


async def test_full_crawl(acme_site: None) -> None:
    pages, truncated = await _crawl(CrawlConfig(seed_url=BASE, seed_host=HOST))

    # Every on-host page is fetched — including the two that error — and nothing else.
    assert set(pages) == {
        "https://acme.test/",
        "https://acme.test/about",
        "https://acme.test/products",
        "https://acme.test/contact",
        "https://acme.test/missing",
        "https://acme.test/broken",
    }
    assert truncated is False

    # Off-host links (other domain and subdomain) are listed but never fetched.
    for offsite in (
        "https://blog.acme.test/",
        "https://partner.example/",
        "https://partner.example/deals",
    ):
        assert offsite not in pages

    # Links are absolute, sorted, and deduped; subdomain + offsite are listed,
    # while relative/fragment forms collapse onto one URL and non-http schemes drop.
    assert pages["https://acme.test/"].links == (
        "https://acme.test/about",
        "https://acme.test/contact",
        "https://acme.test/products",
        "https://blog.acme.test/",
        "https://partner.example/",
    )
    assert pages["https://acme.test/about"].links == (
        "https://acme.test/",
        "https://acme.test/broken",
        "https://acme.test/missing",
        "https://acme.test/products",
    )
    assert pages["https://acme.test/products"].links == (
        "https://acme.test/",
        "https://acme.test/contact",
        "https://partner.example/deals",
    )
    assert pages["https://acme.test/contact"].links == ("https://acme.test/",)

    # The 404 and the transport failure are surfaced, and the crawl carried on.
    missing = pages["https://acme.test/missing"]
    assert missing.status == 404
    assert missing.error is None
    assert missing.links == ()

    broken = pages["https://acme.test/broken"]
    assert broken.status is None
    assert broken.error == "ConnectError: connection refused"
    assert broken.links == ()

    # The real renderers produce the expected JSONL and text output.
    assert json.loads(format_jsonl(pages["https://acme.test/"])) == {
        "url": "https://acme.test/",
        "links": [
            "https://acme.test/about",
            "https://acme.test/contact",
            "https://acme.test/products",
            "https://blog.acme.test/",
            "https://partner.example/",
        ],
        "status": 200,
        "error": None,
    }
    assert (
        format_text(broken) == "https://acme.test/broken  [error: ConnectError: connection refused]"
    )


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_max_pages_truncates(acme_site: None) -> None:
    pages, truncated = await _crawl(CrawlConfig(seed_url=BASE, seed_host=HOST, max_pages=2))

    # The seed plus its first on-host link (alphabetical), then stop; cap reported.
    assert set(pages) == {"https://acme.test/", "https://acme.test/about"}
    assert truncated is True
