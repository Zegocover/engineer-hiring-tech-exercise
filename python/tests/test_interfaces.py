from typing import Any

import pytest

from site_crawler.interfaces import Fetcher, Parser, Writer
from site_crawler.models import ConfigError, CrawlConfig, FetchError, FetchResult, PageResult


@pytest.mark.parametrize(
    "url", ["example.com", "ftp://example.com/", "/relative", "https://", "mailto:a@b.c"]
)
def test_invalid_base_url_rejected(url: str) -> None:
    with pytest.raises(ConfigError):
        CrawlConfig(base_url=url)


@pytest.mark.parametrize("url", ["https://example.com", "http://example.com:8080/start"])
def test_valid_base_url_accepted(url: str) -> None:
    assert CrawlConfig(base_url=url).base_url == url


@pytest.mark.parametrize(
    "kwargs",
    [{"concurrency": 0}, {"max_pages": 0}, {"max_depth": -1}, {"timeout": 0}],
)
def test_invalid_limits_rejected(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ConfigError):
        CrawlConfig("https://example.com", **kwargs)


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        ("text/html; charset=utf-8", True),
        ("application/xhtml+xml", True),
        ("application/pdf", False),
        (None, False),
    ],
)
def test_fetch_result_is_html(content_type: str | None, expected: bool) -> None:
    page = FetchResult("u", "u", 200, content_type, b"")
    assert page.is_html is expected


# Plain classes with no package base classes. Assigning them to the protocol
# types below makes mypy verify structural conformance.
class PlainFetcher:
    async def fetch(self, url: str) -> FetchResult:
        return FetchResult(url, url, 200, "text/html", b"")

    async def aclose(self) -> None:
        pass


class PlainParser:
    def parse(self, page: FetchResult) -> list[str]:
        return []


class PlainWriter:
    async def write(self, result: PageResult) -> None:
        pass

    async def aclose(self) -> None:
        pass


def test_plain_classes_satisfy_protocols() -> None:
    fetcher: Fetcher = PlainFetcher()
    parser: Parser = PlainParser()
    writer: Writer = PlainWriter()
    assert all(c is not None for c in (fetcher, parser, writer))


def test_fetch_error_carries_url_and_reason() -> None:
    err = FetchError("https://example.com/", "HTTP 500")
    assert err.url == "https://example.com/"
    assert "HTTP 500" in str(err)


def test_allowed_hosts_default_to_none() -> None:
    config = CrawlConfig("https://example.com")
    assert config.allowed_hosts == ()
    assert config.per_host_concurrency is None


def test_allowed_hosts_normalised_and_deduplicated() -> None:
    config = CrawlConfig(
        "https://example.com",
        allowed_hosts=("Docs.Partner.IO", "*.example.com", "docs.partner.io", " localhost:8001 "),
    )
    assert config.allowed_hosts == ("docs.partner.io", "*.example.com", "localhost:8001")
    assert [str(p) for p in config.host_patterns] == list(config.allowed_hosts)


@pytest.mark.parametrize("pattern", ["https://other.org/", "*", "exa*mple.com", ""])
def test_invalid_allowed_host_rejected(pattern: str) -> None:
    with pytest.raises(ConfigError, match="invalid host pattern"):
        CrawlConfig("https://example.com", allowed_hosts=(pattern,))


def test_per_host_concurrency_must_be_positive() -> None:
    with pytest.raises(ConfigError, match="per_host_concurrency"):
        CrawlConfig("https://example.com", per_host_concurrency=0)
