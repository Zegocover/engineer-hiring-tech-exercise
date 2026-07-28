import logging
from typing import ClassVar

import httpx
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Log, Static

from crawler.config import DEFAULT_REQUEST_TIMEOUT, USER_AGENT
from crawler.crawler import (
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_MAX_RETRIES,
    Crawler,
    RetryPolicy,
)
from crawler.output import write_result

SPIDER_ART = r"""

    +-----------------------------------------------
    :". /  /  /
    :.-". /  /
    : _.-". /
    :"  _.-".
    :-""     ".
    :
    :
  ^.-.^
 '^\+/^` "Fairwell... Aragog" - Professor Slughorn April 21st 1997
 '/`"'\`

"""

DEFAULT_TIMEOUT = 30.0


class TextualLogHandler(logging.Handler):
    """Forwards stdlib log records to a Textual `Log` widget.

    `emit` always runs on the crawl worker, which shares the app's event
    loop (it's an async Textual worker, not a separate thread), so writing
    to the widget directly is safe - `call_from_thread` would block trying
    to hand work back to the very loop it's running on.
    """

    def __init__(self, log_widget: Log) -> None:
        super().__init__()
        self.log_widget = log_widget

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        self.log_widget.write_line(message)


class UrlScreen(Screen):
    """Step 1: collect the URL to crawl."""

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("I solemnly swear that I am up to no good.", id="oath")
            yield Input(
                placeholder="Enter a URL to crawl, e.g. https://example.com",
                id="url_input",
            )
            yield Static(SPIDER_ART, id="spider")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#url_input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        url = event.value.strip()
        if not url:
            return
        self.app.push_screen(ConfirmScreen(url))


class ConfirmScreen(Screen):
    """Step 2: review/adjust concurrency and retry settings before crawling."""

    BINDINGS: ClassVar = [("escape", "app.pop_screen", "Back")]

    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static(f"Target: {self.url}", id="target")
            yield Label("Max concurrent workers:")
            yield Input(
                value=str(DEFAULT_MAX_CONCURRENCY),
                id="concurrency_input",
                type="integer",
            )
            yield Label("Max retries per page (on 429/5xx):")
            yield Input(
                value=str(DEFAULT_MAX_RETRIES),
                id="retries_input",
                type="integer",
            )
            yield Label("Timeout (seconds):")
            yield Input(
                value=str(DEFAULT_TIMEOUT),
                id="timeout_input",
                type="number",
            )
            with Vertical(id="actions"):
                yield Button("Start crawl", id="confirm", variant="success")
                yield Button("Back", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
            return
        self._confirm()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._confirm()

    def _confirm(self) -> None:
        max_concurrency = int(self.query_one("#concurrency_input", Input).value)
        max_retries = int(self.query_one("#retries_input", Input).value)
        timeout = float(self.query_one("#timeout_input", Input).value)
        self.app.push_screen(
            CrawlScreen(self.url, max_concurrency, max_retries, timeout)
        )


class CrawlScreen(Screen):
    """Step 3: run the crawl and show results."""

    def __init__(
        self, url: str, max_concurrency: int, max_retries: int, timeout: float
    ) -> None:
        super().__init__()
        self.url = url
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries
        self.timeout = timeout

    DEFAULT_CSS = """
    CrawlScreen {
        Vertical {
            height: 1fr;
        }
        #summary {
            height: auto;
        }
        #results {
            height: 1fr;
            border: solid $accent;
        }
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static(
                f"Crawling {self.url} "
                f"(workers={self.max_concurrency}, retries={self.max_retries}, "
                f"timeout={self.timeout}s)",
                id="summary",
            )
            yield Log(id="results")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self.crawl(), exclusive=True)

    async def crawl(self) -> None:
        log = self.query_one("#results", Log)
        log.write_line(f"Crawling {self.url}...")

        handler = TextualLogHandler(log)
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        crawler_logger = logging.getLogger("crawler")
        crawler_logger.addHandler(handler)
        crawler_logger.setLevel(logging.INFO)
        try:
            limits = httpx.Limits(
                max_connections=self.max_concurrency,
                max_keepalive_connections=self.max_concurrency,
            )
            retry_policy = RetryPolicy(max_retries=self.max_retries)
            async with httpx.AsyncClient(
                limits=limits,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
                timeout=DEFAULT_REQUEST_TIMEOUT,
            ) as client:
                result = await Crawler(retry_policy=retry_policy).crawl(
                    client,
                    self.url,
                    timeout=self.timeout,
                    max_concurrency=self.max_concurrency,
                )
        except httpx.HTTPError as exc:
            log.write_line(f"Error: {exc}")
            return
        finally:
            crawler_logger.removeHandler(handler)

        log.write_line(f"Completed: {result.completed}")
        log.write_line(f"Visited {len(result.visited)} page(s):")
        for visited_url in sorted(result.visited):
            log.write_line(f"  - {visited_url}")

        found = result.found_urls_by_domain
        log.write_line(f"Found URLs across {len(found)} domain(s):")
        for domain in sorted(found):
            log.write_line(f"  {domain} ({len(found[domain])})")

        try:
            output_path = write_result(result, self.url)
        except OSError as exc:
            log.write_line(f"Could not write results: {exc}")
        else:
            log.write_line(f"Wrote {output_path}")

        log.write_line("Mischief managed.")


class CrawlerTUI(App):
    BINDINGS: ClassVar = [("ctrl+c", "quit", "Quit")]

    def on_mount(self) -> None:
        self.push_screen(UrlScreen())

    def action_quit(self) -> None:
        self.exit()


def run() -> None:
    CrawlerTUI().run()


if __name__ == "__main__":
    run()
