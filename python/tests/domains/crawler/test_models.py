import dataclasses

import pytest

from domains.crawler.models import CrawlConfig, FetchResult, PageResult, ParseOutcome


def test_fetch_result_is_frozen() -> None:
    fr = FetchResult(
        requested_url="http://a.com/",
        final_url="http://a.com/",
        status=200,
        content_type="text/html",
        html="<html></html>",
        error=None,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        fr.status = 500  # type: ignore[misc]  # ty: ignore[invalid-assignment]


def test_page_result_holds_sorted_links_tuple() -> None:
    pr = PageResult(
        url="http://a.com/",
        links=("http://a.com/a", "http://a.com/b"),
        status=200,
        error=None,
    )
    assert pr.links == ("http://a.com/a", "http://a.com/b")
    assert isinstance(pr.links, tuple)


def test_parse_outcome_pairs_page_with_candidates() -> None:
    page = PageResult(url="http://a.com/", links=(), status=200, error=None)
    outcome = ParseOutcome(page=page, on_host_links=("http://a.com/x",))
    assert outcome.page is page
    assert outcome.on_host_links == ("http://a.com/x",)


def test_crawl_config_defaults_and_seed_host() -> None:
    cfg = CrawlConfig(seed_url="http://a.com/", seed_host="a.com")
    assert cfg.concurrency == 10
    assert cfg.timeout == 10.0
    assert cfg.max_pages is None
    assert cfg.user_agent.startswith("crawler/")
    assert cfg.max_bytes == 5_000_000
