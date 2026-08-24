"""Pure, tolerant DOM operations over HTML bytes."""

from __future__ import annotations

import lxml.html

from .urls import absolutize


def extract_anchor_urls(body: bytes, page_url: str) -> list[str]:
    """Return anchor targets in document order as absolute, fragment-free URLs."""
    if not body.strip():
        return []
    document = lxml.html.fromstring(body)

    base = page_url
    declared = document.xpath("//base[@href]/@href")
    if declared:
        base = absolutize(page_url, str(declared[0]))

    links: list[str] = []
    for href in document.xpath("//a[@href]/@href"):
        raw = str(href).strip()
        if raw:
            links.append(absolutize(base, raw))
    return links
