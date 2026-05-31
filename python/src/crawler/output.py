"""Render PageResult to human text or JSONL. Pure: returns strings, no I/O."""

import json

from domains.crawler.models import PageResult


def format_text(page: PageResult) -> str:
    """One line for the page URL, then each link indented two spaces beneath."""
    if page.error is not None:
        return f"{page.url}  [error: {page.error}]"
    lines = [page.url]
    lines.extend(f"  {link}" for link in page.links)
    return "\n".join(lines)


def format_jsonl(page: PageResult) -> str:
    """A single compact JSON object (one line) for the page."""
    return json.dumps(
        {
            "url": page.url,
            "links": list(page.links),
            "status": page.status,
            "error": page.error,
        },
        separators=(",", ":"),
    )
