"""CLI integration tests."""

import pytest

from crawler import cli


def test_cli_rejects_invalid_base_url() -> None:
    parser = cli.build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["not-a-url"])
    assert exc.value.code == 2


def test_cli_accepts_valid_base_url() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["https://example.com"])
    assert args.base_url == "https://example.com"
