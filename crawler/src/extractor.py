from __future__ import annotations

from typing import Protocol

from selectolax.parser import HTMLParser

from crawler.src.normaliser import DefaultURLNormaliser, URLNormaliser


class ContentExtractor(Protocol):
    def extract_content(self, html: str, base_url: str) -> list[str]: ...


class LinkContentExtractor:
    def __init__(self, normaliser: URLNormaliser | None = None) -> None:
        self._normaliser = normaliser or DefaultURLNormaliser()

    @staticmethod
    def _should_exclude_link(
        normalised: str | None, current_page: str | None, seen: set[str]
    ) -> bool:
        return normalised == current_page or normalised in seen

    def extract_content(self, html: str, base_url: str) -> list[str]:
        html_parser = HTMLParser(html)
        current_page = self._normaliser.normalise_url(base_url, base_url)

        seen: set[str] = set()
        links = []
        for node in html_parser.css("a[href]"):
            href = node.attributes.get("href")

            if not href:
                continue

            normalised = self._normaliser.normalise_url(href, base_url)

            if normalised is None:
                continue

            if self._should_exclude_link(normalised, current_page, seen):
                continue

            seen.add(normalised)
            links.append(normalised)

        return links