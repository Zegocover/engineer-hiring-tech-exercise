from __future__ import annotations

from site_crawler.core import Crawler
from site_crawler.core.robots import RobotsGate
from site_crawler.models import CrawlConfig
from tests.fakes import CollectingWriter, FakeSite, LineParser

BASE = "https://example.com/"
ROBOTS = "https://example.com/robots.txt"
PRIVATE = "https://example.com/private/x"
PAGES = {BASE: ["/private/x", "/public"], "https://example.com/public": [], PRIVATE: []}
RULES = b"User-agent: *\nDisallow: /private/\n"


def site_with_robots() -> FakeSite:
    return FakeSite(PAGES, raw={ROBOTS: RULES}, content_types={ROBOTS: "text/plain"})


async def test_disallowed_url_reported_but_not_fetched() -> None:
    site = site_with_robots()
    writer = CollectingWriter()
    stats = await Crawler(CrawlConfig(BASE), fetcher=site, parser=LineParser(), writer=writer).run()
    assert PRIVATE in writer.as_dict()[BASE]
    assert PRIVATE not in site.calls
    assert "https://example.com/public" in site.calls
    assert stats.robots_skipped == 1


async def test_robots_disabled_fetches_everything() -> None:
    site = site_with_robots()
    await Crawler(
        CrawlConfig(BASE, respect_robots=False),
        fetcher=site,
        parser=LineParser(),
        writer=CollectingWriter(),
    ).run()
    assert PRIVATE in site.calls
    assert ROBOTS not in site.calls


async def test_missing_robots_allows_all() -> None:
    gate = await RobotsGate.load(FakeSite({}), BASE, "test-agent")
    assert gate.allowed(PRIVATE)


async def test_user_agent_specific_rules() -> None:
    site = FakeSite(
        {},
        raw={ROBOTS: b"User-agent: badbot\nDisallow: /\n"},
        content_types={ROBOTS: "text/plain"},
    )
    assert (await RobotsGate.load(site, BASE, "goodbot")).allowed(PRIVATE)
    assert not (await RobotsGate.load(site, BASE, "badbot")).allowed(PRIVATE)
