"""Full crawl through the real HTTP fetcher and HTML parser against a mocked site."""

from __future__ import annotations

import respx

from site_crawler import CrawlConfig, Crawler
from site_crawler.fetchers import HttpxFetcher
from tests.fakes import CollectingWriter

S = "https://example.com"
HTML = {"content-type": "text/html; charset=utf-8"}


def page(*hrefs: str) -> str:
    return "<html><body>" + "".join(f'<a href="{h}">{h}</a>' for h in hrefs) + "</body></html>"


def mock_site(router: respx.MockRouter) -> None:
    router.get(f"{S}/robots.txt").respond(
        200, headers={"content-type": "text/plain"}, text="User-agent: *\nDisallow: /private/\n"
    )
    router.get(f"{S}/").respond(
        200,
        headers=HTML,
        text=page(
            "/a",
            "b",
            "/old",
            "/go",
            "/doc.pdf",
            "https://external.org/",
            "/broken",
            "/private/secret",
            "mailto:hi@example.com",
        ),
    )
    router.get(f"{S}/a").respond(200, headers=HTML, text=page("/b", "/", "/a#top"))
    router.get(f"{S}/b").respond(200, headers=HTML, text=page("c"))
    router.get(f"{S}/c").respond(200, headers=HTML, text=page())
    router.get(f"{S}/old").respond(301, headers={"location": "/new/"})
    router.get(f"{S}/new/").respond(200, headers=HTML, text=page("page"))
    router.get(f"{S}/new/page").respond(200, headers=HTML, text=page("/"))
    router.get(f"{S}/go").respond(302, headers={"location": "https://other.org/landing"})
    router.get("https://other.org/landing").respond(200, headers=HTML, text=page("/elsewhere"))
    router.get(f"{S}/doc.pdf").respond(
        200, headers={"content-type": "application/pdf"}, content=b"%PDF"
    )
    router.get(f"{S}/broken").respond(500)


async def test_full_crawl() -> None:
    async with respx.mock(assert_all_called=False) as router:
        await _run_full_crawl(router)


async def _run_full_crawl(router: respx.MockRouter) -> None:
    mock_site(router)
    secret = router.get(f"{S}/private/secret").respond(200, headers=HTML, text=page())
    elsewhere = router.get("https://other.org/elsewhere").respond(200, headers=HTML, text="")
    writer = CollectingWriter()

    stats = await Crawler(
        CrawlConfig(f"{S}/", concurrency=4),
        fetcher=HttpxFetcher(backoff=0),
        writer=writer,
    ).run()

    assert writer.as_dict() == {
        f"{S}/": (
            f"{S}/a",
            f"{S}/b",
            f"{S}/old",
            f"{S}/go",
            f"{S}/doc.pdf",
            "https://external.org/",
            f"{S}/broken",
            f"{S}/private/secret",
        ),
        f"{S}/a": (f"{S}/b", f"{S}/", f"{S}/a"),
        f"{S}/b": (f"{S}/c",),
        f"{S}/c": (),
        f"{S}/new/": (f"{S}/new/page",),
        f"{S}/new/page": (f"{S}/",),
    }
    assert len(writer.results) == 6  # no page reported twice
    assert stats.pages == 6
    assert stats.fetched == 8  # 6 pages + off-host redirect + PDF
    assert stats.errors == 1
    assert stats.error_urls == [f"{S}/broken"]
    assert stats.robots_skipped == 1
    assert stats.seed_ok
    assert not secret.called
    assert not elsewhere.called
