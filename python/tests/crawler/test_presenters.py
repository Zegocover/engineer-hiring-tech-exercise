import json

from crawler.presenters import format_jsonl, format_text
from domains.crawler.models import PageResult


def test_format_text_lists_url_then_indented_links() -> None:
    pr = PageResult(
        url="http://a.com/",
        links=("http://a.com/a", "http://b.com/x"),
        status=200,
        error=None,
    )
    assert format_text(pr) == ("http://a.com/\n  http://a.com/a\n  http://b.com/x")


def test_format_text_marks_errors() -> None:
    pr = PageResult(url="http://a.com/x", links=(), status=None, error="timeout")
    assert format_text(pr) == "http://a.com/x  [error: timeout]"


def test_format_jsonl_is_one_compact_json_object() -> None:
    pr = PageResult(
        url="http://a.com/",
        links=("http://a.com/a",),
        status=200,
        error=None,
    )
    line = format_jsonl(pr)
    assert "\n" not in line
    parsed = json.loads(line)
    assert parsed == {
        "url": "http://a.com/",
        "links": ["http://a.com/a"],
        "status": 200,
        "error": None,
    }
