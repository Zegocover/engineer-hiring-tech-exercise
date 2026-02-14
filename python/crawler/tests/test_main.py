from __future__ import annotations

import pytest

from crawler import main as main_module
from crawler.crawler import Crawler


def test_main_parses_args_and_calls_crawler(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def _crawl(self) -> None:
        captured["called"] = True
        captured["instance"] = self
        return None

    monkeypatch.setattr(Crawler, "crawl", _crawl)

    result = main_module.main(
        [
            "https://example.com",
            "--batch-size",
            "5",
            "--max-urls",
            "25",
            "--timeout",
            "3.5",
            "--retries",
            "2",
            "--quiet",
        ]
    )

    assert result == 0
    assert captured.get("called") is True
    instance = captured.get("instance")
    assert isinstance(instance, Crawler)
    assert instance._batch_size == 5
    assert instance._max_urls == 25
    assert instance._timeout == 3.5
    assert instance._retries == 2
    assert instance._quiet is True


def test_output_defaults_to_json(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def _crawl(self) -> None:
        captured["instance"] = self
        return None

    monkeypatch.setattr(Crawler, "crawl", _crawl)

    result = main_module.main(["https://example.com", "--output", "out.json"])

    assert result == 0
    instance = captured.get("instance")
    assert isinstance(instance, Crawler)
    assert instance._quiet is False


@pytest.mark.parametrize(
    "args",
    [
        ["https://example.com", "--batch-size", "0"],
        ["https://example.com", "--batch-size", "11"],
        ["https://example.com", "--max-urls", "0"],
        ["https://example.com", "--max-urls", "1001"],
        ["https://example.com", "--timeout", "-0.1"],
        ["https://example.com", "--timeout", "10.1"],
        ["https://example.com", "--retries", "-1"],
        ["https://example.com", "--retries", "4"],
    ],
)
def test_argument_constraints(args: list[str]) -> None:
    with pytest.raises(SystemExit):
        main_module.main(args)
