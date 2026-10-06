"""Tests for the Crawler orchestrator, using an in-memory FakeFetcher.

No network is involved: FakeFetcher serves a canned link-graph so we can assert
exactly which URLs get fetched, in what multiplicity, and what each page reports.
"""

from __future__ import annotations

import pytest

from crawler.crawler import Crawler
from crawler.extractor import LinkExtractor
from crawler.models import FetchResult, PageResult

BASE = "http://example.com/"


def _html(hrefs: list[str]) -> str:
    body = "".join(f'<a href="{href}">link</a>' for href in hrefs)
    return f"<html><body>{body}</body></html>"


def page(url: str, hrefs: list[str], *, final_url: str | None = None) -> FetchResult:
    return FetchResult(
        requested_url=url,
        final_url=final_url or url,
        status_code=200,
        content_type="text/html",
        text=_html(hrefs),
    )


def non_html(url: str, content_type: str = "application/pdf") -> FetchResult:
    return FetchResult(
        requested_url=url,
        final_url=url,
        status_code=200,
        content_type=content_type,
        text=None,
    )


class FakeFetcher:
    """Serves canned FetchResults and records the order of calls."""

    def __init__(self, pages: dict[str, FetchResult]) -> None:
        self._pages = pages
        self.calls: list[str] = []

    async def fetch(self, url: str) -> FetchResult:
        self.calls.append(url)
        try:
            return self._pages[url]
        except KeyError:
            return FetchResult(requested_url=url, final_url=url, status_code=404)


async def crawl_all(
    fetcher: FakeFetcher, base_url: str = BASE, **kwargs: object
) -> list[PageResult]:
    crawler = Crawler(fetcher, LinkExtractor(), base_url=base_url, **kwargs)  # type: ignore[arg-type]
    return [page async for page in crawler.crawl()]


def crawled_urls(pages: list[PageResult]) -> set[str]:
    return {p.url for p in pages}


# ---------------------------------------------------------------------------
# Traversal, cycles and de-duplication
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("concurrency", [1, 4])
async def test_traverses_all_reachable_pages_exactly_once(concurrency: int) -> None:
    fetcher = FakeFetcher(
        {
            BASE: page(BASE, ["http://example.com/a", "http://example.com/b"]),
            "http://example.com/a": page("http://example.com/a", ["http://example.com/b", BASE]),
            "http://example.com/b": page(
                "http://example.com/b", ["http://example.com/a", "http://example.com/c"]
            ),
            "http://example.com/c": page("http://example.com/c", []),
        }
    )

    pages = await crawl_all(fetcher, concurrency=concurrency)

    assert crawled_urls(pages) == {
        BASE,
        "http://example.com/a",
        "http://example.com/b",
        "http://example.com/c",
    }
    # Cycles (a<->b, a->home) must not cause any page to be fetched twice.
    assert sorted(fetcher.calls) == sorted(set(fetcher.calls))


async def test_duplicate_fragment_and_case_variants_collapse_to_one_fetch() -> None:
    fetcher = FakeFetcher(
        {
            BASE: page(
                BASE,
                [
                    "http://example.com/a",
                    "http://example.com/a#frag",  # fragment stripped when scheduling
                    "http://EXAMPLE.com/a",  # host case-insensitive
                ],
            ),
            "http://example.com/a": page("http://example.com/a", []),
        }
    )

    pages = await crawl_all(fetcher)

    assert fetcher.calls == [BASE, "http://example.com/a"]
    # The page still faithfully reports all three distinct hrefs it contained.
    home = next(p for p in pages if p.url == BASE)
    assert len(home.links) == 3


# ---------------------------------------------------------------------------
# Domain scoping
# ---------------------------------------------------------------------------


async def test_offdomain_links_are_reported_but_not_followed() -> None:
    fetcher = FakeFetcher(
        {BASE: page(BASE, ["http://example.com/a", "https://external.com/x"])},
    )
    fetcher._pages["http://example.com/a"] = page("http://example.com/a", [])

    pages = await crawl_all(fetcher)

    assert "https://external.com/x" not in fetcher.calls
    home = next(p for p in pages if p.url == BASE)
    assert "https://external.com/x" in home.links  # still reported


async def test_subdomains_excluded_by_default_included_on_request() -> None:
    def build() -> FakeFetcher:
        return FakeFetcher(
            {
                BASE: page(BASE, ["http://blog.example.com/x"]),
                "http://blog.example.com/x": page("http://blog.example.com/x", []),
            }
        )

    default = build()
    await crawl_all(default)
    assert default.calls == [BASE]  # blog subdomain not followed

    widened = build()
    await crawl_all(widened, include_subdomains=True)
    assert "http://blog.example.com/x" in widened.calls


# ---------------------------------------------------------------------------
# Redirects
# ---------------------------------------------------------------------------


async def test_relative_links_resolve_against_post_redirect_url() -> None:
    fetcher = FakeFetcher(
        {
            BASE: page(BASE, ["http://example.com/old"]),
            # /old redirects to /new/ and its relative link "sub" must resolve
            # against /new/, not against /old.
            "http://example.com/old": page(
                "http://example.com/old", ["sub"], final_url="http://example.com/new/"
            ),
            "http://example.com/new/sub": page("http://example.com/new/sub", []),
        }
    )

    pages = await crawl_all(fetcher)

    assert "http://example.com/new/sub" in fetcher.calls
    assert "http://example.com/new/" not in fetcher.calls  # reached only via redirect
    old = next(p for p in pages if p.url == "http://example.com/old")
    assert old.links == ("http://example.com/new/sub",)


async def test_offdomain_redirect_body_is_not_parsed() -> None:
    fetcher = FakeFetcher(
        {
            BASE: page(BASE, ["http://example.com/gone"]),
            "http://example.com/gone": page(
                "http://example.com/gone",
                ["http://external.com/e2"],
                final_url="https://external.com/e",
            ),
        }
    )

    pages = await crawl_all(fetcher)

    assert "http://external.com/e2" not in fetcher.calls
    gone = next(p for p in pages if p.url == "http://example.com/gone")
    assert gone.links == ()  # off-domain content is not mined for links


# ---------------------------------------------------------------------------
# Content types, errors and limits
# ---------------------------------------------------------------------------


async def test_non_html_pages_are_reported_with_no_links() -> None:
    fetcher = FakeFetcher(
        {
            BASE: page(BASE, ["http://example.com/doc.pdf"]),
            "http://example.com/doc.pdf": non_html("http://example.com/doc.pdf"),
        }
    )

    pages = await crawl_all(fetcher)

    doc = next(p for p in pages if p.url == "http://example.com/doc.pdf")
    assert doc.links == ()


async def test_fetch_errors_are_reported_and_do_not_stop_the_crawl() -> None:
    fetcher = FakeFetcher(
        {
            BASE: page(BASE, ["http://example.com/ok", "http://example.com/bad"]),
            "http://example.com/ok": page("http://example.com/ok", []),
            "http://example.com/bad": FetchResult(
                requested_url="http://example.com/bad",
                final_url="http://example.com/bad",
                error="connection refused",
            ),
        }
    )

    pages = await crawl_all(fetcher)

    assert crawled_urls(pages) == {BASE, "http://example.com/ok", "http://example.com/bad"}
    bad = next(p for p in pages if p.url == "http://example.com/bad")
    assert bad.error == "connection refused"


async def test_worker_survives_unexpected_exceptions() -> None:
    # A fetcher that *raises* (a bug, not a handled transport error) must not
    # take the whole crawl down; the page is reported with the error instead.
    class RaisingFetcher(FakeFetcher):
        async def fetch(self, url: str) -> FetchResult:
            self.calls.append(url)
            if url == "http://example.com/boom":
                raise RuntimeError("kaboom")
            return self._pages[url]

    fetcher = RaisingFetcher(
        {
            BASE: page(BASE, ["http://example.com/boom", "http://example.com/ok"]),
            "http://example.com/ok": page("http://example.com/ok", []),
        }
    )

    pages = await crawl_all(fetcher)

    boom = next(p for p in pages if p.url == "http://example.com/boom")
    assert boom.error is not None and "RuntimeError" in boom.error
    assert "http://example.com/ok" in crawled_urls(pages)  # crawl kept going


async def test_max_pages_caps_the_crawl() -> None:
    fetcher = FakeFetcher(
        {
            BASE: page(
                BASE,
                [
                    "http://example.com/a",
                    "http://example.com/b",
                    "http://example.com/c",
                ],
            ),
            "http://example.com/a": page("http://example.com/a", []),
            "http://example.com/b": page("http://example.com/b", []),
            "http://example.com/c": page("http://example.com/c", []),
        }
    )

    pages = await crawl_all(fetcher, max_pages=2)

    assert len(pages) == 2
    assert len(fetcher.calls) == 2
    assert BASE in crawled_urls(pages)


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------


def test_rejects_base_url_without_host() -> None:
    with pytest.raises(ValueError, match="absolute http"):
        Crawler(FakeFetcher({}), LinkExtractor(), base_url="not-a-url")


def test_rejects_non_positive_concurrency() -> None:
    with pytest.raises(ValueError, match="concurrency"):
        Crawler(FakeFetcher({}), LinkExtractor(), base_url=BASE, concurrency=0)
