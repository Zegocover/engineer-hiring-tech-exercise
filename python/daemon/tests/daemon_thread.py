"""A real daemon on its own event loop in a background thread, for driving the blocking CLI."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any

from site_crawler.interfaces import Fetcher

from crawl_daemon.client import DaemonClient
from crawl_daemon.server import loop_factory, run_daemon
from crawl_daemon.settings import Settings
from crawl_daemon.state import DaemonState


class DaemonThread:
    def __init__(self, data_dir: Path, site: Fetcher, **settings: Any) -> None:
        self.data_dir = data_dir
        self.site = site
        self.settings = Settings(data_dir=str(data_dir), port=0, **settings)
        self.state: DaemonState | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.error: BaseException | None = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, name="crawld-test", daemon=True)

    def _run(self) -> None:
        async def main() -> None:
            self.loop = asyncio.get_running_loop()
            await run_daemon(
                self.settings,
                fetcher_factory=lambda: self.site,
                on_ready=self._on_ready,
                flush_interval=0.01,
            )

        try:
            asyncio.run(main(), loop_factory=loop_factory)
        except BaseException as exc:
            self.error = exc
        finally:
            self._ready.set()

    def _on_ready(self, state: DaemonState) -> None:
        self.state = state
        self._ready.set()

    def start(self) -> DaemonThread:
        self._thread.start()
        if not self._ready.wait(10) or self.state is None:
            raise RuntimeError(f"the test daemon did not start: {self.error!r}")
        return self

    def call_soon(self, callback: Any) -> None:
        """Run ``callback`` on the daemon's loop (e.g. to open a fake site's gate)."""
        assert self.loop is not None
        self.loop.call_soon_threadsafe(callback)

    def stop(self) -> None:
        if self._thread.is_alive():
            DaemonClient(self.data_dir).ping() and DaemonClient(self.data_dir).call("shutdown")
            self._thread.join(15)
