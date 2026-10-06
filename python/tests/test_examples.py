from __future__ import annotations

from examples.custom_writer import build_graph

from tests.fakes import FakeSite

BASE = "https://example.com/"


def html(*hrefs: str) -> bytes:
    return "".join(f'<a href="{h}">x</a>' for h in hrefs).encode()


async def test_custom_writer_example_runs_without_subclassing() -> None:
    site = FakeSite(
        {},
        raw={
            BASE: html("/a", "/b"),
            "https://example.com/a": html("/b"),
            "https://example.com/b": html("/"),
        },
    )
    graph = await build_graph(BASE, fetcher=site)
    assert set(graph.graph) == {BASE, "https://example.com/a", "https://example.com/b"}
    assert graph.most_linked(1) == [("https://example.com/b", 2)]
    assert graph.closed
