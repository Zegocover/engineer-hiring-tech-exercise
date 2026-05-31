from typing import get_type_hints

from domains.crawler import ports


def test_ports_are_protocols() -> None:
    # Every port is a typing.Protocol subclass (has the protocol marker).
    for name in (
        "Fetcher",
        "LinkExtractor",
        "Queue",
        "RobotsPolicy",
        "FetchStage",
        "ParseStage",
    ):
        cls = getattr(ports, name)
        assert getattr(cls, "_is_protocol", False), f"{name} is not a Protocol"


def test_fetcher_signature() -> None:
    hints = get_type_hints(ports.Fetcher.fetch)
    assert "url" in hints
