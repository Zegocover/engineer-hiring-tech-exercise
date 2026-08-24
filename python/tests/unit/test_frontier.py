from __future__ import annotations

from crawler.webcrawler.frontier import Frontier
from crawler.webcrawler.politeness import Politeness


def _frontier(robots_text: str | None = None) -> Frontier:
    return Frontier("http://h/", Politeness.from_robots(robots_text, "zego"))


def test_scope_filters_and_dedup() -> None:
    frontier = _frontier()
    links = [
        "http://h/a",
        "http://other/b",  # off-host
        "https://h/c",  # same host, https
        "mailto:x@h",  # non-http
        "http://h/a",  # duplicate
    ]
    assert frontier.admit(links) == ["http://h/a", "https://h/c"]


def test_seen_persists_across_calls() -> None:
    frontier = _frontier()
    assert frontier.admit(["http://h/a"]) == ["http://h/a"]
    assert frontier.admit(["http://h/a"]) == []


def test_base_url_starts_seen() -> None:
    assert _frontier().admit(["http://h/"]) == []


def test_robots_disallow_excluded_from_scope() -> None:
    frontier = _frontier("User-agent: *\nDisallow: /no")
    assert frontier.admit(["http://h/no/x", "http://h/yes"]) == ["http://h/yes"]
