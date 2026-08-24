from __future__ import annotations

from crawler.webcrawler.politeness import Politeness

DISALLOW = "User-agent: *\nDisallow: /private"


def _politeness(text: str | None, user_agent: str = "zego") -> Politeness:
    return Politeness.from_robots(text, user_agent)


def test_missing_file_allows_all() -> None:
    assert _politeness(None).allowed("http://h/anything")


def test_disallow_blocks_prefix_only() -> None:
    politeness = _politeness(DISALLOW)
    assert not politeness.allowed("http://h/private/x")
    assert politeness.allowed("http://h/public")


def test_user_agent_specific_rule() -> None:
    text = "User-agent: zego\nDisallow: /\n\nUser-agent: *\nDisallow:"
    assert not _politeness(text, "zego").allowed("http://h/x")
    assert _politeness(text, "other").allowed("http://h/x")
