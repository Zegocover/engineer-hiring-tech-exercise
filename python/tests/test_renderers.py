"""Tests for output renderers."""

import json

from crawler.renderers import JsonRenderer, TextRenderer


def test_text_renderer(tmp_path) -> None:
    path = tmp_path / "out.txt"
    renderer = TextRenderer(path)
    renderer.write_page("https://example.com", ["/a", "/b"])
    renderer.write_page("https://example.com/2", [])
    renderer.close()

    assert path.read_text() == (
        "https://example.com\n" "  - /a\n" "  - /b\n" "https://example.com/2\n"
    )


def test_json_renderer(tmp_path) -> None:
    path = tmp_path / "out.json"
    renderer = JsonRenderer(path)
    renderer.write_page("https://example.com", ["/a", "/b"])
    first = json.loads(path.read_text())
    assert first == [
        {"page_url": "https://example.com", "links": ["/a", "/b"]},
    ]
    renderer.write_page("https://example.com/2", [])
    renderer.close()

    data = json.loads(path.read_text())
    assert data == [
        {"page_url": "https://example.com", "links": ["/a", "/b"]},
        {"page_url": "https://example.com/2", "links": []},
    ]
