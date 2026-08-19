import pytest

from site_crawler.cli import build_parser, main


def test_cli_requires_a_base_url() -> None:
    parser = build_parser()

    args = parser.parse_args(["https://example.test"])

    assert args.base_url == "https://example.test"
    assert args.depth is None


def test_cli_accepts_a_maximum_depth() -> None:
    parser = build_parser()

    args = parser.parse_args(["https://example.test", "--depth", "2"])

    assert args.depth == 2


def test_cli_rejects_missing_base_url() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])


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
        "site_crawler.cli.extract_links_from_url", lambda url: []
    )

    with caplog.at_level("INFO"):
        main(arguments)

    assert message in caplog.text
