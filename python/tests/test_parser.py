import pytest

from site_crawler.parser import extract_links, extract_links_from_url


class FakeResponse:
    text = '<a href="/docs">Docs</a>'

    def raise_for_status(self) -> None:
        pass


class NoLinksResponse:
    text = "<html><body><p>No links here.</p></body></html>"

    def raise_for_status(self) -> None:
        pass


def test_extract_links_resolves_relative_urls_and_drops_fragments() -> None:
    html = (
        '<a href="/docs#intro">Docs</a><a href="https://other.test">Other</a>'
    )

    assert extract_links(html, "https://example.test/start") == (
        "https://example.test/docs",
        "https://other.test/",
    )


def test_extract_links_can_include_duplicates() -> None:
    html = '<a href="/docs">One</a><a href="/docs">Two</a>'

    assert extract_links(html, "https://example.test", True) == (
        "https://example.test/docs",
        "https://example.test/docs",
    )


def test_extract_links_from_url_fetches_and_parses_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "site_crawler.parser.httpx.get",
        lambda url, headers, timeout: FakeResponse(),
    )

    assert extract_links_from_url("https://example.test/start") == [
        "https://example.test/docs"
    ]


def test_extract_links_from_url_returns_empty_list_when_page_has_no_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "site_crawler.parser.httpx.get",
        lambda url, headers, timeout: NoLinksResponse(),
    )

    assert extract_links_from_url("https://example.test") == []
