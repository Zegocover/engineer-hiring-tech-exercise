from __future__ import annotations

import pytest
import respx

from site_crawler import CrawlConfig, Crawler

HTML = {"content-type": "text/html"}


@respx.mock
async def test_defaults_only_crawl_writes_text(capsys: pytest.CaptureFixture[str]) -> None:
    respx.get("https://example.com/robots.txt").respond(404)
    respx.get("https://example.com/").respond(
        200, headers=HTML, text='<a href="/a">a</a><a href="https://other.org/">o</a>'
    )
    respx.get("https://example.com/a").respond(200, headers=HTML, text='<a href="/">home</a>')

    stats = await Crawler(CrawlConfig("https://example.com/")).run()

    assert capsys.readouterr().out == (
        "https://example.com/\n"
        "  https://example.com/a\n"
        "  https://other.org/\n"
        "https://example.com/a\n"
        "  https://example.com/\n"
    )
    assert stats.pages == 2
    assert stats.seed_ok
