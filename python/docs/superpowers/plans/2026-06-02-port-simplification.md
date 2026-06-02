# Port Simplification & Parsing-in-Domain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the crawler's ports to the two genuine external-system seams (`Fetcher`, `Queue`), move HTML link extraction into the domain core, and make the engine own its internal pipeline instead of receiving injected stages.

**Architecture:** `SelectolaxExtractor` moves from `src/gateways/parsing/` into `src/domains/crawler/extractor.py` (it is a pure, no-I/O transformation). `DefaultParseStage` constructs and owns the extractor. The robots gate and `DefaultFetchStage` are deleted; the engine's workers call the `Fetcher` port directly and the engine builds its own `DefaultParseStage`. The `LinkExtractor`, `RobotsPolicy`, `FetchStage`, and `ParseStage` Protocols are removed.

**Tech Stack:** Python 3.13, `uv`, `pytest` (asyncio_mode=auto), `ruff`, `ty`, `selectolax`, `httpx`, `typer`. Reference spec: `docs/superpowers/specs/2026-06-02-port-simplification-design.md`.

**Conventions:**
- Run everything from the `python/` directory.
- The CI gate is `make check` (= format-check + lint + typecheck + test). It must pass before every commit.
- If `ruff` reports formatting after edits, run `make fix` (ruff format → ruff check --fix → ruff format) then re-run `make check`.
- This is a behaviour-preserving refactor. The TDD rhythm per task is: change the test to the new shape → run it and watch it fail for the expected reason → change the source → run it green → `make check` → commit. The `tests/e2e/*` suite and `tests/crawler/test_factory.py` are **regression guards — do not modify them**; they must stay green throughout.

---

## File Structure

**Source — created:**
- `src/domains/crawler/extractor.py` — `SelectolaxExtractor`, the in-domain HTML link extractor.

**Source — modified:**
- `src/domains/crawler/stages/parse_stage.py` — `DefaultParseStage(seed_host)` builds + owns the extractor.
- `src/domains/crawler/engine.py` — `Crawler(config, fetcher, frontier, results)`; builds its own parse stage; worker calls the fetcher directly.
- `src/domains/crawler/ports.py` — keep only `Fetcher` and `Queue`.
- `src/domains/crawler/__init__.py` — drop `DefaultFetchStage`, `NoOpRobotsPolicy` from the public surface.
- `src/crawler/factory.py` — wire only `HttpxFetcher` + two `InMemoryQueue`s + `Crawler`.

**Source — deleted:**
- `src/domains/crawler/robots.py`
- `src/domains/crawler/stages/fetch_stage.py`
- `src/gateways/parsing/` (whole package: `__init__.py` + `selectolax_extractor.py`)

**Tests — created:** `tests/domains/crawler/test_extractor.py` (moved from gateways).
**Tests — modified:** `tests/test_cli.py`, `tests/test_architecture.py`, `tests/domains/crawler/test_engine.py`, `tests/domains/crawler/stages/test_parse_stage.py`, `tests/domains/crawler/test_ports.py`, `tests/domains/crawler/test_public_surface.py`.
**Tests — deleted:** `tests/gateways/parsing/test_selectolax_extractor.py` (+ the now-empty `tests/gateways/parsing/` package), `tests/domains/crawler/stages/test_fetch_stage.py`, `tests/domains/crawler/test_robots.py`.
**Tests — untouched (regression guards):** `tests/crawler/test_factory.py`, `tests/e2e/*`.

**Docs — modified:** `README.md`.

---

## Task 1: Repair the red baseline

The last commit renamed `build_crawler` → `crawler_factory` in `src/crawler/cli.py` but `tests/test_cli.py` still patches the old name, so 3 CLI tests fail with `AttributeError: ... has no attribute 'build_crawler'`. Start from green by fixing the patch target. This is independent of the refactor.

**Files:**
- Modify: `tests/test_cli.py` (the `_patch_build` helper, around line 25-26)

- [ ] **Step 1: Confirm the failing baseline**

Run: `uv run pytest tests/test_cli.py -q`
Expected: 3 failed (`test_crawl_prints_pages_as_text`, `test_crawl_json_outputs_jsonl`, `test_crawl_prints_truncation_notice`), each `AttributeError: <module 'crawler.cli' ...> has no attribute 'build_crawler'`.

- [ ] **Step 2: Fix the patch target**

In `tests/test_cli.py`, change the `_patch_build` helper:

```python
def _patch_build(monkeypatch: pytest.MonkeyPatch, crawler: FakeCrawler) -> None:
    monkeypatch.setattr(cli_module, "crawler_factory", lambda config, client: crawler)
```

(Only the patched attribute name changes: `"build_crawler"` → `"crawler_factory"`.)

- [ ] **Step 3: Run the CLI tests**

Run: `uv run pytest tests/test_cli.py -q`
Expected: all pass.

- [ ] **Step 4: Run the full gate**

Run: `make check`
Expected: exit 0; pytest reports 76 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_cli.py
git commit -m "test(crawler): fix cli test patching renamed crawler_factory

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Move link extraction into the domain

Create `SelectolaxExtractor` inside the domain, have `DefaultParseStage` own it, drop the `LinkExtractor` Protocol, and narrow the architecture boundary test so a pure (no-I/O) parsing library is allowed in the domain. The fetch stage / robots / engine constructor are untouched here (handled in Task 3).

**Files:**
- Modify: `tests/test_architecture.py` (the `_FORBIDDEN_PREFIXES` tuple)
- Create: `src/domains/crawler/extractor.py`
- Modify: `src/domains/crawler/stages/parse_stage.py`
- Modify: `src/crawler/factory.py` (parse-stage construction only)
- Modify: `src/domains/crawler/ports.py` (remove `LinkExtractor`)
- Create: `tests/domains/crawler/test_extractor.py`
- Delete: `src/gateways/parsing/selectolax_extractor.py`, `src/gateways/parsing/__init__.py`
- Delete: `tests/gateways/parsing/test_selectolax_extractor.py`, `tests/gateways/parsing/__init__.py`
- Modify: `tests/domains/crawler/stages/test_parse_stage.py` (full rewrite — drop the FakeExtractor)
- Modify: `tests/domains/crawler/test_engine.py` (parse-stage construction + drop RealishExtractor)
- Modify: `tests/domains/crawler/test_ports.py` (remove `LinkExtractor` from the list)

- [ ] **Step 1: Narrow the architecture boundary test**

The domain may use pure in-process libraries (selectolax) but still no I/O/framework libs or outer layers. In `tests/test_architecture.py`, remove `"selectolax"` from the forbidden prefixes:

```python
_FORBIDDEN_PREFIXES = ("httpx", "typer", "asyncer", "crawler", "gateways")
```

- [ ] **Step 2: Run the architecture test (still green)**

Run: `uv run pytest tests/test_architecture.py -q`
Expected: pass (selectolax is not yet imported in the domain; the rule is just looser).

- [ ] **Step 3: Move the extractor test (write it against the new home, expect failure)**

Create `tests/domains/crawler/test_extractor.py` with the full content below. It imports from the domain and calls `extract(html)` with no `base_url`:

```python
from domains.crawler.extractor import SelectolaxExtractor


def test_extracts_anchor_area_and_link_hrefs() -> None:
    html = """
    <html><body>
      <a href="/a">a</a>
      <area href="/b">
      <link rel="canonical" href="/c">
      <a>no href</a>
    </body></html>
    """
    hrefs = SelectolaxExtractor().extract(html)
    assert set(hrefs) == {"/a", "/b", "/c"}


def test_handles_malformed_html() -> None:
    html = '<a href="/x">unclosed <a href="/y">'
    hrefs = SelectolaxExtractor().extract(html)
    assert "/x" in hrefs
    assert "/y" in hrefs


def test_resolves_against_base_href_when_present() -> None:
    html = '<head><base href="http://a.com/sub/"></head><body><a href="x">x</a></body>'
    hrefs = SelectolaxExtractor().extract(html)
    # With a <base>, the relative href resolves against the base.
    assert "http://a.com/sub/x" in hrefs


def test_empty_html_returns_empty_list() -> None:
    assert SelectolaxExtractor().extract("") == []
```

- [ ] **Step 4: Run the new extractor test (expect failure)**

Run: `uv run pytest tests/domains/crawler/test_extractor.py -q`
Expected: collection/import error — `ModuleNotFoundError: No module named 'domains.crawler.extractor'`.

- [ ] **Step 5: Create the in-domain extractor**

Create `src/domains/crawler/extractor.py`:

```python
"""SelectolaxExtractor: pull navigation hrefs from HTML (fast, lenient parsing).

This is a pure, in-process transformation — no network, no filesystem — so it is
domain logic, not a gateway. It is strategy-shaped (a different parser could
replace it) but is used concretely; no port is defined for it until a second
implementation actually exists.

Pulls href from <a>, <area>, and <link>. If the document declares a <base href>,
relative hrefs are resolved against it here (a <base> overrides the page URL, so
the parse stage cannot do this on its own). Page-relative resolution for the
common no-<base> case happens downstream in urls.normalize()."""

from urllib.parse import urljoin

from selectolax.parser import HTMLParser

_HREF_TAGS = ("a", "area", "link")


class SelectolaxExtractor:
    """Extract navigation hrefs from HTML using selectolax."""

    def extract(self, html: str) -> list[str]:
        tree = HTMLParser(html)
        base = self._base_href(tree)
        hrefs: list[str] = []
        for tag in _HREF_TAGS:
            for node in tree.css(tag):
                href = node.attributes.get("href")
                if href:
                    hrefs.append(urljoin(base, href) if base else href)
        return hrefs

    @staticmethod
    def _base_href(tree: HTMLParser) -> str | None:
        node = tree.css_first("base[href]")
        if node is None:
            return None
        return node.attributes.get("href") or None
```

- [ ] **Step 6: Run the extractor test (expect pass)**

Run: `uv run pytest tests/domains/crawler/test_extractor.py -q`
Expected: 4 passed.

- [ ] **Step 7: Delete the old gateway extractor + its test**

```bash
git rm src/gateways/parsing/selectolax_extractor.py src/gateways/parsing/__init__.py
git rm tests/gateways/parsing/test_selectolax_extractor.py tests/gateways/parsing/__init__.py
```

(Removes the now-empty `src/gateways/parsing/` and `tests/gateways/parsing/` packages.)

- [ ] **Step 8: Rewrite the parse-stage test to drop the FakeExtractor**

Replace the entire contents of `tests/domains/crawler/stages/test_parse_stage.py` with:

```python
from domains.crawler.models import FetchResult
from domains.crawler.stages.parse_stage import DefaultParseStage


def _html_result(url: str, html: str) -> FetchResult:
    return FetchResult(
        requested_url=url,
        final_url=url,
        status=200,
        content_type="text/html",
        html=html,
        error=None,
    )


async def test_links_are_normalized_sorted_and_deduped() -> None:
    html = (
        '<a href="/b">b</a><a href="/a">a</a>'
        '<a href="/a#frag">a-frag</a><a href="mailto:x@a.com">mail</a>'
    )
    stage = DefaultParseStage(seed_host="a.com")
    outcome = await stage.parse(_html_result("http://a.com/", html))
    # mailto dropped; /a and /a#frag collapse; sorted.
    assert outcome.page.links == ("http://a.com/a", "http://a.com/b")


async def test_on_host_vs_offsite_classification() -> None:
    html = (
        '<a href="http://a.com/p">p</a>'
        '<a href="http://www.a.com/q">q</a>'
        '<a href="http://b.com/r">r</a>'
    )
    stage = DefaultParseStage(seed_host="a.com")
    outcome = await stage.parse(_html_result("http://a.com/", html))
    # All three are listed on the page...
    assert outcome.page.links == (
        "http://a.com/p",
        "http://b.com/r",
        "http://www.a.com/q",
    )
    # ...but only the exact-host one is an enqueue candidate (subdomain excluded).
    assert outcome.on_host_links == ("http://a.com/p",)


async def test_links_resolved_against_final_url_after_redirect() -> None:
    stage = DefaultParseStage(seed_host="a.com")
    # href="x" is page-relative; it must resolve against final_url's directory
    # (/new/), not the requested_url (/old). So the result is /new/x, proving the
    # parse stage uses final_url.
    result = FetchResult(
        requested_url="http://a.com/old",
        final_url="http://a.com/new/page",
        status=200,
        content_type="text/html",
        html='<a href="x">x</a>',
        error=None,
    )
    outcome = await stage.parse(result)
    assert outcome.page.links == ("http://a.com/new/x",)
    assert outcome.page.url == "http://a.com/new/page"


async def test_non_html_yields_empty_links_and_no_candidates() -> None:
    stage = DefaultParseStage(seed_host="a.com")
    result = FetchResult(
        requested_url="http://a.com/file.pdf",
        final_url="http://a.com/file.pdf",
        status=200,
        content_type="application/pdf",
        html=None,
        error=None,
    )
    outcome = await stage.parse(result)
    assert outcome.page.links == ()
    assert outcome.on_host_links == ()


async def test_error_result_passes_through_with_no_links() -> None:
    stage = DefaultParseStage(seed_host="a.com")
    result = FetchResult(
        requested_url="http://a.com/boom",
        final_url="http://a.com/boom",
        status=None,
        content_type=None,
        html=None,
        error="timeout",
    )
    outcome = await stage.parse(result)
    assert outcome.page.error == "timeout"
    assert outcome.page.links == ()
    assert outcome.on_host_links == ()
```

- [ ] **Step 9: Run the parse-stage test (expect failure)**

Run: `uv run pytest tests/domains/crawler/stages/test_parse_stage.py -q`
Expected: `TypeError` — `DefaultParseStage.__init__()` still requires the old `extractor` argument (the source hasn't changed yet).

- [ ] **Step 10: Make ParseStage own the extractor**

Replace the entire contents of `src/domains/crawler/stages/parse_stage.py` with:

```python
"""Stage 2: turn a FetchResult into a PageResult + on-host enqueue candidates."""

from domains.crawler.extractor import SelectolaxExtractor
from domains.crawler.models import FetchResult, PageResult, ParseOutcome
from domains.crawler.urls import normalize, same_host


class DefaultParseStage:
    """Extract links, normalize them, and split on-host from off-site.

    Owns its HTML extractor directly: extraction is a pure in-domain transform,
    so there is no port to inject.
    """

    def __init__(self, seed_host: str) -> None:
        self._seed_host = seed_host
        self._extractor = SelectolaxExtractor()

    async def parse(self, result: FetchResult) -> ParseOutcome:
        if result.html is None:
            page = PageResult(
                url=result.final_url,
                links=(),
                status=result.status,
                error=result.error,
            )
            return ParseOutcome(page=page, on_host_links=())

        normalized: set[str] = set()
        for href in self._extractor.extract(result.html):
            canonical = normalize(href, result.final_url)
            if canonical is not None:
                normalized.add(canonical)

        all_links = tuple(sorted(normalized))
        on_host = tuple(u for u in all_links if same_host(u, self._seed_host))
        page = PageResult(
            url=result.final_url,
            links=all_links,
            status=result.status,
            error=result.error,
        )
        return ParseOutcome(page=page, on_host_links=on_host)
```

- [ ] **Step 11: Run the parse-stage test (expect pass)**

Run: `uv run pytest tests/domains/crawler/stages/test_parse_stage.py -q`
Expected: 5 passed.

- [ ] **Step 12: Update the factory's parse-stage construction**

In `src/crawler/factory.py`: remove the `from gateways.parsing.selectolax_extractor import SelectolaxExtractor` import, and change the parse-stage line to no longer pass an extractor. The relevant line becomes:

```python
    parse_stage = DefaultParseStage(seed_host=config.seed_host)
```

(Everything else in the factory stays as-is for now; the fetch stage and `Crawler(...)` call are reworked in Task 3.)

- [ ] **Step 13: Remove the LinkExtractor port**

In `src/domains/crawler/ports.py`, delete the `LinkExtractor` Protocol block (the `@runtime_checkable class LinkExtractor(Protocol): ... extract(self, html, base_url) ...`). Leave `Fetcher`, `Queue`, `RobotsPolicy`, `FetchStage`, `ParseStage` (the last three are removed in Task 3). Keep the `from domains.crawler.models import FetchResult, ParseOutcome` import (still used by `FetchStage`/`ParseStage`).

- [ ] **Step 14: Drop LinkExtractor from the ports test**

In `tests/domains/crawler/test_ports.py`, remove `"LinkExtractor",` from the name tuple in `test_ports_are_protocols`. The tuple becomes:

```python
    for name in (
        "Fetcher",
        "Queue",
        "RobotsPolicy",
        "FetchStage",
        "ParseStage",
    ):
```

- [ ] **Step 15: Update the engine test's parse-stage construction**

In `tests/domains/crawler/test_engine.py`: delete the `RealishExtractor` class entirely, and change the `parse_stage` line in `_build` to drop the extractor argument:

```python
    parse_stage = DefaultParseStage(seed_host="a.com")
```

(The `FakeFetcher` already serves real `<a href=...>` HTML, so the real `SelectolaxExtractor` now owned by the parse stage parses it correctly and all assertions still hold. The `fetch_stage` line and `Crawler(...)` call are reworked in Task 3.)

- [ ] **Step 16: Run the full gate**

Run: `make check`
Expected: exit 0; all tests pass (green). The suite is one test smaller than Task 1 (the `LinkExtractor` port-conformance test was dropped). If formatting fails, run `make fix` then re-run `make check`.

- [ ] **Step 17: Commit**

```bash
git add -A
git commit -m "refactor(crawler): move link extraction into the domain core

SelectolaxExtractor is a pure no-I/O transform, so it belongs in the domain,
not behind a gateway port. DefaultParseStage now owns it directly; the
LinkExtractor Protocol and the unused extract() base_url param are gone. The
architecture boundary test is narrowed to allow pure parsing libs in the domain.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Collapse the stages — engine owns its pipeline

Remove the robots gate and `DefaultFetchStage` (which, without robots, is a pure pass-through to the `Fetcher`). The engine's workers call the `Fetcher` port directly, and the engine builds its own `DefaultParseStage`. The composition root now hands the engine only its two external collaborators (the fetcher and the queues). Ports shrink to `Fetcher` + `Queue`.

**Files:**
- Modify: `src/domains/crawler/engine.py`
- Modify: `src/crawler/factory.py`
- Modify: `src/domains/crawler/ports.py` (remove `RobotsPolicy`, `FetchStage`, `ParseStage`)
- Modify: `src/domains/crawler/__init__.py`
- Delete: `src/domains/crawler/robots.py`, `src/domains/crawler/stages/fetch_stage.py`
- Modify: `tests/domains/crawler/test_engine.py`
- Modify: `tests/domains/crawler/test_ports.py`
- Modify: `tests/domains/crawler/test_public_surface.py`
- Delete: `tests/domains/crawler/test_robots.py`, `tests/domains/crawler/stages/test_fetch_stage.py`

- [ ] **Step 1: Rewrite the engine test wiring (expect failure)**

In `tests/domains/crawler/test_engine.py`, replace the imports at the top and the `_build` helper so the engine receives a `fetcher` (not stages). The full new top-of-file (down to and including `_build`) is:

```python
from domains.crawler.engine import Crawler
from domains.crawler.models import CrawlConfig, FetchResult
from gateways.memory.queue import InMemoryQueue


class FakeFetcher:
    """Serves HTML from an in-memory {url: html} graph; 404s unknown URLs."""

    def __init__(self, pages: dict[str, str]) -> None:
        self._pages = pages

    async def fetch(self, url: str) -> FetchResult:
        if url in self._pages:
            return FetchResult(
                requested_url=url,
                final_url=url,
                status=200,
                content_type="text/html",
                html=self._pages[url],
                error=None,
            )
        return FetchResult(
            requested_url=url,
            final_url=url,
            status=404,
            content_type=None,
            html=None,
            error="not found",
        )


def _build(pages: dict[str, str], seed: str, max_pages: int | None = None) -> Crawler:
    config = CrawlConfig(seed_url=seed, seed_host="a.com", concurrency=3, max_pages=max_pages)
    return Crawler(
        config=config,
        fetcher=FakeFetcher(pages),
        frontier=InMemoryQueue(),
        results=InMemoryQueue(),
    )
```

Leave every `test_*` function below `_build` unchanged.

- [ ] **Step 2: Run the engine test (expect failure)**

Run: `uv run pytest tests/domains/crawler/test_engine.py -q`
Expected: `TypeError` — `Crawler.__init__()` got an unexpected keyword argument `fetcher` (engine not reworked yet).

- [ ] **Step 3: Rework the engine to own its pipeline**

Replace the imports and the `__init__`/`_worker` of `src/domains/crawler/engine.py`. The import block becomes:

```python
import asyncio
from collections.abc import AsyncIterator

from domains.crawler.models import CrawlConfig, FetchResult, PageResult
from domains.crawler.ports import Fetcher, Queue
from domains.crawler.stages.parse_stage import DefaultParseStage
```

The constructor becomes:

```python
    def __init__(
        self,
        config: CrawlConfig,
        fetcher: Fetcher,
        frontier: Queue[str],
        results: Queue[FetchResult],
    ) -> None:
        self._config = config
        self._fetcher = fetcher
        self._parse_stage = DefaultParseStage(config.seed_host)
        self._frontier = frontier
        self._results = results
        self._visited: set[str] = set()
        self._in_flight = 0
        self._truncated = False
```

The worker becomes (call the fetcher directly):

```python
    async def _worker(self) -> None:
        while True:
            url = await self._frontier.get()
            result = await self._fetcher.fetch(url)
            await self._results.put(result)
```

Leave `crawl`, `_process_one`, `_enqueue_if_new`, `_enqueue`, `_at_cap`, `truncated`, `_spawn_workers`, `_stop_workers` unchanged (`_process_one` still calls `self._parse_stage.parse(result)`; the class docstring may stay as-is).

- [ ] **Step 4: Run the engine test (expect pass)**

Run: `uv run pytest tests/domains/crawler/test_engine.py -q`
Expected: all pass.

- [ ] **Step 5: Simplify the factory**

Replace the entire contents of `src/crawler/factory.py` with:

```python
"""Composition root wiring: assemble a Crawler from config + an httpx client."""

import httpx

from domains.crawler.engine import Crawler
from domains.crawler.models import CrawlConfig, FetchResult
from domains.crawler.ports import Queue
from gateways.http.httpx_fetcher import HttpxFetcher
from gateways.memory.queue import InMemoryQueue


def crawler_factory(config: CrawlConfig, client: httpx.AsyncClient) -> Crawler:
    """Wire the real fetcher gateway + in-memory queues into a Crawler.

    The engine builds its own parse stage; the composition root only supplies the
    genuinely external collaborators (the HTTP fetcher and the queues).
    """
    # This could be done with a DI framework, but we're keeping it simple here.
    fetcher = HttpxFetcher(client, max_bytes=config.max_bytes)
    # Annotate the locals so the generic queue type is inferred for `ty`.
    frontier: Queue[str] = InMemoryQueue()
    results: Queue[FetchResult] = InMemoryQueue()
    return Crawler(
        config=config,
        fetcher=fetcher,
        frontier=frontier,
        results=results,
    )
```

- [ ] **Step 6: Delete robots + fetch stage and their tests**

```bash
git rm src/domains/crawler/robots.py src/domains/crawler/stages/fetch_stage.py
git rm tests/domains/crawler/test_robots.py tests/domains/crawler/stages/test_fetch_stage.py
```

- [ ] **Step 7: Trim the ports to the two real boundaries**

Replace the entire contents of `src/domains/crawler/ports.py` with:

```python
"""Ports (Protocols) the engine depends on — the two genuine external-system
boundaries. Implementations live in gateways. Defined here so dependencies
point inward."""

from typing import Protocol, runtime_checkable

from domains.crawler.models import FetchResult


@runtime_checkable
class Fetcher(Protocol):
    """Fetch one URL over the network. Implemented by a gateway (httpx)."""

    async def fetch(self, url: str) -> FetchResult: ...


@runtime_checkable
class Queue[T](Protocol):
    """Minimal generic message queue. In-memory now; broker (Kafka/SQS) later."""

    async def put(self, item: T) -> None: ...
    async def get(self) -> T: ...
```

- [ ] **Step 8: Update the domain public surface**

Replace the entire contents of `src/domains/crawler/__init__.py` with:

```python
"""Public surface of the crawler domain."""

from domains.crawler.engine import Crawler
from domains.crawler.models import CrawlConfig, FetchResult, PageResult, ParseOutcome
from domains.crawler.stages.parse_stage import DefaultParseStage

__all__ = [
    "CrawlConfig",
    "Crawler",
    "DefaultParseStage",
    "FetchResult",
    "PageResult",
    "ParseOutcome",
]
```

- [ ] **Step 9: Update the ports test**

In `tests/domains/crawler/test_ports.py`, set the name tuple in `test_ports_are_protocols` to exactly the two surviving ports:

```python
    for name in (
        "Fetcher",
        "Queue",
    ):
```

(Leave `test_fetcher_signature` unchanged.)

- [ ] **Step 10: Update the public-surface test**

In `tests/domains/crawler/test_public_surface.py`, remove `DefaultFetchStage` and `NoOpRobotsPolicy` from both the import and the asserts. The full file becomes:

```python
def test_public_names_importable_from_package_root() -> None:
    from domains.crawler import (
        CrawlConfig,
        Crawler,
        DefaultParseStage,
        FetchResult,
        PageResult,
        ParseOutcome,
    )

    assert Crawler is not None
    assert CrawlConfig is not None
    assert DefaultParseStage is not None
    assert FetchResult is not None
    assert PageResult is not None
    assert ParseOutcome is not None
```

- [ ] **Step 11: Run the full gate**

Run: `make check`
Expected: exit 0; all tests pass (green). The suite is smaller again (the robots and fetch-stage tests were deleted). If formatting fails, run `make fix` then re-run `make check`.

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "refactor(crawler): engine owns its pipeline; drop robots + fetch stage

Removing the robots gate leaves DefaultFetchStage a pure pass-through, so it and
the RobotsPolicy/FetchStage/ParseStage ports are deleted. Workers call the
Fetcher port directly and the engine builds its own parse stage; the factory now
supplies only the fetcher and queues. Ports reduce to Fetcher + Queue.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Update the README

Bring the architecture docs in line with the new structure. Several references are also stale from the earlier rename commit (`build_crawler`/`builder.py`/`output.py`) — fix those too.

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the layer diagram + descriptions**

In `README.md`, in the `### Architecture & design` section: in the mermaid `flowchart TD`, change the gateways node so it no longer lists the extractor:

```
    GW["src/gateways<br/>httpx fetcher · in-memory queue"]
```

Then replace the three layer bullets that follow it with:

```markdown
- **`src/domains/crawler`** — the inner core: the `engine` coordinator, the parse
  `stage`, the link `extractor`, the `ports` (Protocols), the frozen `models`, and
  URL logic. It performs no I/O — it uses selectolax purely for in-process HTML
  parsing, but makes no network or filesystem calls.
- **`src/gateways`** — outward adapters that implement the domain ports: an httpx
  fetcher and an in-memory queue.
- **`src/crawler`** — the CLI composition root: the Typer app, the `crawler_factory`
  wiring, and the text/JSONL output renderers.
```

- [ ] **Step 2: Update the boundary-test description**

Replace the paragraph that begins "The domain core depends on nothing outward..." with:

```markdown
The domain core depends on nothing outward; the CLI and gateways depend on the
domain's ports. A test (`tests/test_architecture.py`) AST-scans the domain and
fails the build if it ever imports an I/O or framework library (httpx, typer,
asyncer) or an outer layer (`crawler`, `gateways`), so the boundary cannot
silently rot. A pure parsing library (selectolax) is allowed: it does no I/O.
```

- [ ] **Step 3: Update the crawl-pipeline prose + diagram**

Replace the "Two stages joined by two queues..." sentence with:

```markdown
A fetch fan-out feeding a single parse loop, joined by two queues. N fetch workers
run concurrently (the workload is I/O-bound); one parse loop owns all shared
state, so no locks are needed.
```

In the `flowchart LR`, change the fetch-workers node so it no longer mentions a robots gate:

```
    FR --> FW["fetch workers ×N<br/>(httpx fetch)"]
```

- [ ] **Step 4: Update the design-decision bullets**

Replace the "Ports + manual dependency injection" bullet and the "selectolax + httpx" bullet with:

```markdown
- **Ports for external seams only.** The two genuine I/O boundaries — `Fetcher`
  (HTTP) and `Queue` (transport) — are `typing.Protocol`s defined in the domain,
  so the HTTP client and queue are each swappable and the engine is tested
  end-to-end with zero network using fakes. Link extraction is a pure in-domain
  transform used concretely, not behind a port — no interface is introduced until
  a second implementation exists. Wiring is a few lines in `crawler_factory`; an
  exercise this size does not need a DI framework.
- **selectolax + httpx.** Chosen for speed and a clean async API. httpx sits
  behind the `Fetcher` port (a different client is a one-file change); selectolax
  is used directly inside the parse stage as the link-extraction strategy.
```

- [ ] **Step 5: Reframe robots.txt as future work**

Replace the "robots.txt is a NoOp placeholder" bullet under `### Trade-offs & future work` with:

```markdown
- **robots.txt is not implemented (future work).** There is no robots handling
  today. A production crawler must fetch, cache, and honor each origin's
  `/robots.txt` — Disallow rules and Crawl-delay, denying on parse failure —
  before running against third-party sites. This was deliberately left out rather
  than stubbed behind a guessed interface; the gate would be reintroduced (likely
  in the fetcher or a dedicated stage) when the real policy is built.
```

- [ ] **Step 6: Fix the project-layout tree**

In the `## Project layout` code block, replace the `src/` tree so it reflects the current files (this also corrects the stale `builder.py`/`output.py`):

```
python/
├── src/
│   ├── crawler/                 # CLI / composition root (outer layer)
│   │   ├── cli.py               # Typer app; the `crawl` command
│   │   ├── factory.py           # wires the fetcher + queues into a Crawler
│   │   ├── presenters.py        # PageResult → text / JSONL
│   │   └── __main__.py          # enables `python -m crawler`
│   ├── domains/crawler/         # domain core (no I/O)
│   │   ├── engine.py            # the async crawl coordinator
│   │   ├── stages/              # parse stage (extract → normalize → classify)
│   │   ├── extractor.py         # selectolax link extractor
│   │   ├── ports.py             # Protocols: Fetcher, Queue
│   │   ├── models.py            # frozen dataclasses
│   │   └── urls.py              # normalize / extract_host / same_host
│   └── gateways/                # adapters (outer layer)
│       ├── http/                # httpx fetcher
│       └── memory/              # in-memory asyncio.Queue adapter
├── tests/                       # pytest suite (outside the package)
└── pyproject.toml               # project metadata, deps, and tool config
```

- [ ] **Step 7: Verify no stale references remain**

Run: `grep -n "build_crawler\|builder.py\|output.py\|LinkExtractor\|RobotsPolicy\|NoOpRobots\|robots placeholder\|selectolax extractor\|stdlib only\|standard library" README.md`
Expected: no matches that describe the old design (the only acceptable hits are the new "future work" robots wording and the new tree). If a stale line remains, fix it to match the new structure.

- [ ] **Step 8: Run the full gate**

Run: `make check`
Expected: exit 0; all tests pass (green) — docs-only change; nothing should regress.

- [ ] **Step 9: Commit**

```bash
git add README.md
git commit -m "docs(crawler): align README with simplified ports + in-domain parsing

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final verification

- [ ] **Run the whole gate once more**

Run: `make check`
Expected: exit 0; all tests pass (green); ruff format + lint clean; `ty` clean.

- [ ] **Confirm the boundary still holds and the deletions are real**

Run: `grep -rn "from gateways.parsing\|LinkExtractor\|RobotsPolicy\|FetchStage\|ParseStage\|NoOpRobotsPolicy\|DefaultFetchStage\|build_crawler" src tests`
Expected: no matches.

- [ ] **Smoke-test the CLI end to end**

Run: `make run ARGS="crawl https://example.com"`
Expected: prints `https://example.com/` with its links beneath; exit 0. (Network-dependent; skip if offline.)
