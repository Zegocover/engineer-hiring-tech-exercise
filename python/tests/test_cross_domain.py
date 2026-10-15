"""Crawls whose scope includes extra hosts (allowed_hosts) and per-host robots.txt."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from site_crawler.core import Crawler
from site_crawler.models import CrawlConfig, CrawlStats
from tests.fakes import CollectingWriter, FakeSite, LineParser

BASE = "https://example.com/"
PARTNER = "https://docs.partner.io/"
ROBOTS_TXT = "text/plain"


async def crawl(
    pages: Mapping[str, list[str]], *, site_kwargs: Mapping[str, Any] | None = None, **config: Any
) -> tuple[FakeSite, CollectingWriter, CrawlStats]:
    config.setdefault("respect_robots", False)
    site = FakeSite(pages, **(site_kwargs or {}))
    writer = CollectingWriter()
    crawler = Crawler(CrawlConfig(BASE, **config), fetcher=site, parser=LineParser(), writer=writer)
    return site, writer, await crawler.run()


async def test_allowed_exact_host_is_followed_with_its_links() -> None:
    pages = {
        BASE: [f"{PARTNER}guide"],
        f"{PARTNER}guide": ["/next", "https://other.org/"],
        f"{PARTNER}next": [],
    }
    site, writer, _ = await crawl(pages, allowed_hosts=("docs.partner.io",))

    assert set(writer.as_dict()) == {BASE, f"{PARTNER}guide", f"{PARTNER}next"}
    assert "https://other.org/" in writer.as_dict()[f"{PARTNER}guide"]
    assert "https://other.org/" not in site.calls


async def test_without_allowed_hosts_other_hosts_are_only_reported() -> None:
    site, writer, _ = await crawl({BASE: [f"{PARTNER}guide"], f"{PARTNER}guide": []})

    assert writer.as_dict() == {BASE: (f"{PARTNER}guide",)}
    assert f"{PARTNER}guide" not in site.calls


async def test_wildcard_covers_subdomains_but_not_other_domains() -> None:
    pages = {
        BASE: ["https://blog.example.com/", "https://a.b.example.com/", "https://example.org/"],
        "https://blog.example.com/": [],
        "https://a.b.example.com/": [],
        "https://example.org/": [],
    }
    site, writer, _ = await crawl(pages, allowed_hosts=("*.example.com",))

    assert "https://blog.example.com/" in site.calls
    assert "https://a.b.example.com/" in site.calls
    assert "https://example.org/" not in site.calls
    assert "https://example.org/" in writer.as_dict()[BASE]


async def test_redirect_to_allowed_host_reported_under_final_url() -> None:
    www = "https://www.example.com/"
    pages = {BASE: ["/go"], www: ["/about"], f"{www}about": []}
    _, writer, _ = await crawl(
        pages,
        allowed_hosts=("www.example.com",),
        site_kwargs={"redirects": {"https://example.com/go": www}},
    )

    assert www in writer.as_dict()
    assert f"{www}about" in writer.as_dict()


async def test_redirect_out_of_scope_still_dropped() -> None:
    pages = {BASE: ["/go"], "https://other.org/": ["/x"]}
    _, writer, _ = await crawl(
        pages,
        allowed_hosts=("docs.partner.io",),
        site_kwargs={"redirects": {"https://example.com/go": "https://other.org/"}},
    )

    assert set(writer.as_dict()) == {BASE}


def robots_site_kwargs(rules: Mapping[str, bytes]) -> dict[str, Any]:
    return {"raw": dict(rules), "content_types": dict.fromkeys(rules, ROBOTS_TXT)}


async def test_robots_txt_read_once_per_host_and_applied_per_host() -> None:
    pages = {
        BASE: [f"{PARTNER}drafts/x", f"{PARTNER}guide", "/drafts/x"],
        "https://example.com/drafts/x": [f"{PARTNER}guide"],
        f"{PARTNER}guide": [f"{PARTNER}drafts/y"],
        f"{PARTNER}drafts/x": [],
        f"{PARTNER}drafts/y": [],
    }
    rules = {f"{PARTNER}robots.txt": b"User-agent: *\nDisallow: /drafts/\n"}
    site, _, stats = await crawl(
        pages,
        respect_robots=True,
        allowed_hosts=("docs.partner.io",),
        site_kwargs=robots_site_kwargs(rules),
    )

    assert site.calls[f"{PARTNER}robots.txt"] == 1
    assert site.calls["https://example.com/robots.txt"] == 1  # 404 from the fake: allow all
    assert "https://example.com/drafts/x" in site.calls  # same path, other host: allowed
    assert f"{PARTNER}guide" in site.calls
    assert f"{PARTNER}drafts/x" not in site.calls
    assert f"{PARTNER}drafts/y" not in site.calls
    assert stats.robots_skipped == 2


async def test_disallowed_urls_on_allowed_host_do_not_use_page_budget() -> None:
    pages = {
        BASE: [f"{PARTNER}drafts/a", f"{PARTNER}drafts/b", f"{PARTNER}ok"],
        f"{PARTNER}ok": [],
    }
    rules = {f"{PARTNER}robots.txt": b"User-agent: *\nDisallow: /drafts/\n"}
    site, _, stats = await crawl(
        pages,
        max_pages=2,
        respect_robots=True,
        allowed_hosts=("docs.partner.io",),
        site_kwargs=robots_site_kwargs(rules),
    )

    assert f"{PARTNER}ok" in site.calls
    assert stats.fetched == 2
    assert stats.robots_skipped == 2


async def test_seed_waits_for_its_hosts_robots_txt() -> None:
    site, _, _ = await crawl({BASE: []}, respect_robots=True)
    assert list(site.calls) == ["https://example.com/robots.txt", BASE]


class InFlightSite(FakeSite):
    """Records the most requests that were ever in flight at once, per host and overall."""

    def __init__(self, pages: Mapping[str, list[str]]) -> None:
        super().__init__(pages)
        self.in_flight: dict[str, int] = {}
        self.peak: dict[str, int] = {}
        self.peak_total = 0

    async def fetch(self, url: str) -> Any:
        host = url.split("/")[2]
        self.in_flight[host] = self.in_flight.get(host, 0) + 1
        self.peak[host] = max(self.peak.get(host, 0), self.in_flight[host])
        self.peak_total = max(self.peak_total, sum(self.in_flight.values()))
        try:
            await asyncio.sleep(0.005)
            return await super().fetch(url)
        finally:
            self.in_flight[host] -= 1


def two_busy_hosts() -> dict[str, list[str]]:
    a = [f"{BASE}{n}" for n in range(12)]
    b = [f"{PARTNER}{n}" for n in range(12)]
    return {BASE: a + b, **{url: [] for url in a + b}}


async def test_per_host_limit_is_never_exceeded() -> None:
    site = InFlightSite(two_busy_hosts())
    config = CrawlConfig(
        BASE,
        concurrency=8,
        per_host_concurrency=2,
        allowed_hosts=("docs.partner.io",),
        respect_robots=False,
    )
    await Crawler(config, fetcher=site, parser=LineParser(), writer=CollectingWriter()).run()

    assert site.peak == {"example.com": 2, "docs.partner.io": 2}
    assert site.peak_total == 4  # both hosts were crawled at the same time


async def test_without_a_per_host_limit_one_host_can_use_all_workers() -> None:
    site = InFlightSite(two_busy_hosts())
    config = CrawlConfig(BASE, concurrency=6, respect_robots=False)
    await Crawler(config, fetcher=site, parser=LineParser(), writer=CollectingWriter()).run()

    assert site.peak["example.com"] == 6
