"""Output renderers for text and JSON formats."""

import json
import threading
from pathlib import Path
from typing import TextIO


class Renderer:
    """Renderer interface for crawl output."""

    def write_page(self, page_url: str, links: list[str]) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class TextRenderer(Renderer):
    """Render output in grouped text format."""

    def __init__(self, path: Path) -> None:
        self._fh: TextIO | None = path.open("w", encoding="utf-8")
        self._lock = threading.Lock()

    def _ensure_open(self) -> TextIO:
        if self._fh is None:
            raise RuntimeError("Renderer is closed")
        return self._fh

    def write_page(self, page_url: str, links: list[str]) -> None:
        with self._lock:
            fh = self._ensure_open()
            fh.write(f"{page_url}\n")
            for link in links:
                fh.write(f"  - {link}\n")
            fh.flush()

    def close(self) -> None:
        with self._lock:
            if self._fh is not None:
                self._fh.close()
                self._fh = None


class JsonRenderer(Renderer):
    """Render output as a streamed JSON array."""

    def __init__(self, path: Path) -> None:
        self._fh: TextIO | None = path.open("w", encoding="utf-8")
        self._fh.write("[]")
        self._first: bool = True
        self._lock = threading.Lock()

    def _ensure_open(self) -> TextIO:
        if self._fh is None:
            raise RuntimeError("Renderer is closed")
        return self._fh

    def write_page(self, page_url: str, links: list[str]) -> None:
        with self._lock:
            fh = self._ensure_open()
            obj = {"page_url": page_url, "links": links}
            payload = json.dumps(obj)
            fh.seek(0, 2)
            fh.seek(fh.tell() - 1)
            if not self._first:
                fh.write(",")
            fh.write(payload)
            fh.write("]")
            self._first = False
            fh.flush()

    def close(self) -> None:
        with self._lock:
            if self._fh is not None:
                self._fh.close()
                self._fh = None
