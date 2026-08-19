import httpx
import pytest

from site_crawler.cli import build_parser, main


def test_cli_requires_a_base_url() -> None:
    parser = build_parser()

    args = parser.parse_args(["wikipedia.org"])

    assert args.base_url == "https://wikipedia.org"
    assert args.depth is None
    assert args.include_duplicates is False


def test_cli_accepts_a_maximum_depth() -> None:
    parser = build_parser()

    args = parser.parse_args(["https://example.test", "--depth", "2"])

    assert args.depth == 2


@pytest.mark.parametrize(
    ("base_url", "normalized_url"),
    [
        ("wikipedia.org", "https://wikipedia.org"),
        ("www.wikipedia.org", "https://www.wikipedia.org"),
        ("http://wikipedia.org", "http://wikipedia.org"),
        ("https://wikipedia.org", "https://wikipedia.org"),
    ],
)
def test_cli_accepts_and_normalizes_base_url(
    base_url: str, normalized_url: str
) -> None:
    parser = build_parser()

    args = parser.parse_args([base_url])

    assert args.base_url == normalized_url


def test_cli_accepts_include_duplicates() -> None:
    parser = build_parser()

    args = parser.parse_args(
        ["https://example.test", "--include-duplicates"]
    )

    assert args.include_duplicates is True


def test_cli_rejects_missing_base_url() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])


@pytest.mark.parametrize(
    "base_url",
    [
        "ftp://example.test",
        "https://",
        "https://bad host",
        "https://example.test:not-a-port",
    ],
)
def test_cli_rejects_invalid_base_url(base_url: str) -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([base_url])


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (
            ["https://Example.test/path"],
            "Starting crawl of example.test (unlimited depth limit)",
        ),
        (
            ["https://example.test", "--depth", "2"],
            "Starting crawl of example.test (2 depth limit)",
        ),
    ],
)
def test_cli_logs_crawl_start(
    arguments: list[str],
    message: str,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "site_crawler.cli.extract_links_from_url",
        lambda url, include_duplicates=False: [],
    )

    with caplog.at_level("INFO"):
        main(arguments)

    assert message in caplog.text


def test_cli_prints_page_error_and_continues_with_other_pages(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    missing_url = "https://example.test/missing"
    working_url = "https://example.test/working"

    def fetch_links(
        url: str, include_duplicates: bool = False
    ) -> list[str]:
        if url == missing_url:
            request = httpx.Request("GET", url)
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError(
                "404 Not Found", request=request, response=response
            )
        if url == "https://example.test":
            return [missing_url, working_url]
        return []

    monkeypatch.setattr(
        "site_crawler.cli.extract_links_from_url", fetch_links
    )

    main(["https://example.test", "--depth", "1"])

    output = capsys.readouterr().out
    assert f"Error fetching {missing_url}:" in output
    assert f"URL: {working_url} contains 0 links:" in output
