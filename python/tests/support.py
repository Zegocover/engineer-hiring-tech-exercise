"""Read-only static file server + the integration case directory, for black-box tests."""

from __future__ import annotations

import contextlib
import functools
import http.server
import threading
from collections.abc import Iterator
from pathlib import Path

CASES_DIR = Path(__file__).parent / "integration" / "cases"


@contextlib.contextmanager
def serve_dir(directory: Path) -> Iterator[str]:
    """Serve ``directory`` on a random localhost port; yields the base URL."""

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            return None

    handler = functools.partial(Handler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/"
    finally:
        server.shutdown()
        thread.join()
