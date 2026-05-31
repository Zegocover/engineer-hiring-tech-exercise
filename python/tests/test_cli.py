from typer.testing import CliRunner

from crawler.cli import app

runner = CliRunner()


def test_help_lists_crawl_command() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "crawl" in result.stdout


def test_crawl_stub_prints_placeholder_and_exits_nonzero() -> None:
    result = runner.invoke(app, ["crawl", "https://example.com"])
    assert result.exit_code == 1
    assert "not implemented" in result.stdout
    assert "https://example.com" in result.stdout
