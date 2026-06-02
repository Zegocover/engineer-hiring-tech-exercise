# Port Simplification & Parsing-in-Domain — Design

**Date:** 2026-06-02
**Branch:** `zegotest`
**Status:** Approved

## Goal

Tighten the crawler's internal boundaries so that **ports model only genuine
external-system seams**, parsing lives where it conceptually belongs (the domain
core), and the engine — not the composition root — owns how its internal pipeline
is built.

## Motivation

The current layering over-abstracts. Three observations drove this work:

1. **`SelectolaxExtractor` is not a gateway.** Link extraction is a *pure, in-process
   transformation* ("given HTML, find the hrefs") with no I/O. It is domain logic
   shaped like a strategy, not an adapter to an external system. It currently lives
   in `src/gateways/parsing/` behind a `LinkExtractor` Protocol that has exactly one
   implementation and one consumer.

2. **The robots policy is speculative.** `NoOpRobotsPolicy` + the `RobotsPolicy`
   Protocol exist as a seam for a feature that isn't built. `allowed()` is unlikely
   to be the final interface (a real policy also needs crawl-delay, per-origin
   caching, deny-on-parse-failure). Keeping a guessed interface now is the kind of
   "interface we don't need yet" worth deleting.

3. **The stages should not be injected.** The composition root currently builds
   `DefaultFetchStage` and `DefaultParseStage` and injects them into the engine. The
   CLI/factory should not need to know how the engine's internals are assembled.
   Both stages have a single implementation, so the `FetchStage`/`ParseStage`
   Protocols add indirection without buying swappability.

These collapse together: once the robots gate is removed (point 2),
`DefaultFetchStage` has **no logic left** — it becomes `return await
self._fetcher.fetch(url)`. So it stops justifying its own existence, and the engine
can call the `Fetcher` port directly.

A pre-existing issue is fixed along the way: commit `b21de9d` ("Rename cli modules
and functions") renamed `build_crawler` → `crawler_factory` in `cli.py` but left
`tests/test_cli.py` patching the old attribute, so 3 CLI tests currently fail with
`AttributeError: ... has no attribute 'build_crawler'`. This work touches that exact
wiring and repairs it.

## Guiding principle

> A **port** exists to abstract a genuine external-system boundary (network, infra),
> not to abstract one pure function behind an interface "just in case."

After this change the surviving ports are exactly the two external seams:

| Port      | Boundary it abstracts                  | Impl now        | Plausible later        |
| --------- | -------------------------------------- | --------------- | ---------------------- |
| `Fetcher` | network I/O                            | `HttpxFetcher`  | aiohttp / other client |
| `Queue[T]`| message transport / infra             | `InMemoryQueue` | Kafka / SQS broker     |

Removed: `LinkExtractor`, `RobotsPolicy`, `FetchStage`, `ParseStage`.

## Architecture (after)

```
src/domains/crawler/
  engine.py              Crawler: owns the Fetcher port + two Queues; builds
                         DefaultParseStage internally; worker calls fetcher.fetch()
  stages/parse_stage.py  DefaultParseStage(seed_host): builds + uses a
                         SelectolaxExtractor; extract → normalize → classify
  extractor.py           SelectolaxExtractor (moved in from gateways); extract(html)
  ports.py               Fetcher, Queue                 (other four Protocols deleted)
  models.py, urls.py     unchanged
  (robots.py deleted; stages/fetch_stage.py deleted)
src/gateways/
  http/httpx_fetcher.py  unchanged
  memory/queue.py        unchanged
  (parsing/ deleted — now empty)
src/crawler/
  factory.py             builds HttpxFetcher + 2 InMemoryQueues + Crawler only
  cli.py, presenters.py  unchanged (cli already calls crawler_factory)
```

### Data flow (after)

```
seed ─▶ frontier queue ─▶ fetch workers ×N ──(fetcher.fetch)──▶ results queue
                                                                     │
                          parse loop ◀────────────────────────────────┘
                          DefaultParseStage.parse:
                            extract (selectolax) → normalize → split on-host/offsite
                          on-host links ─▶ frontier (if new & under cap)
                          PageResult     ─▶ yielded to caller
```

The fetch *stage* disappears; workers call the `Fetcher` port directly. The parse
stage remains a distinct unit (it carries real logic) but is now an engine-internal
detail, constructed by the engine rather than injected.

## Component-by-component changes

### `src/domains/crawler/extractor.py` (new)

Move `SelectolaxExtractor` here from `gateways/parsing/selectolax_extractor.py`,
unchanged except the **unused `base_url` parameter is removed**:

```python
def extract(self, html: str) -> list[str]:
```

The method never used `base_url`. `<base href>` handling stays (it reads the base
from the document itself). Page-relative href resolution already happens downstream
in `normalize(href, result.final_url)` inside the parse stage, so dropping the param
changes no behaviour.

### `src/domains/crawler/stages/parse_stage.py`

- Constructor: `DefaultParseStage(seed_host: str)` — no `extractor` parameter.
- Build the extractor internally: `self._extractor = SelectolaxExtractor()`.
- Call site: `self._extractor.extract(result.html)` (no `base_url`).
- Logic otherwise unchanged (normalize, dedup/sort, split on-host via `same_host`).

### `src/domains/crawler/engine.py`

- Constructor: `Crawler(config, fetcher: Fetcher, frontier: Queue[str], results: Queue[FetchResult])`.
- Build the parse stage internally: `self._parse_stage = DefaultParseStage(config.seed_host)`.
- Worker: `result = await self._fetcher.fetch(url)` (no fetch stage).
- Coordination logic (visited set, in-flight counter, truncation, shutdown) unchanged.

### `src/domains/crawler/ports.py`

Keep `Fetcher` and `Queue`. Delete `LinkExtractor`, `RobotsPolicy`, `FetchStage`,
`ParseStage`.

### `src/domains/crawler/__init__.py`

Remove `DefaultFetchStage` and `NoOpRobotsPolicy` from the imports and `__all__`.
Public surface becomes: `Crawler`, `CrawlConfig`, `FetchResult`, `PageResult`,
`ParseOutcome`, `DefaultParseStage`.

### `src/crawler/factory.py`

```python
def crawler_factory(config: CrawlConfig, client: httpx.AsyncClient) -> Crawler:
    fetcher = HttpxFetcher(client, max_bytes=config.max_bytes)
    frontier: Queue[str] = InMemoryQueue()
    results: Queue[FetchResult] = InMemoryQueue()
    return Crawler(config=config, fetcher=fetcher, frontier=frontier, results=results)
```

No stage/robots/extractor wiring. (`cli.py` already calls `crawler_factory`, so it
needs no change for this refactor — only the test that patches it is fixed.)

### Deletions

- `src/domains/crawler/robots.py`
- `src/domains/crawler/stages/fetch_stage.py`
- `src/gateways/parsing/` (package dir + `__init__.py` + `selectolax_extractor.py`)

## Test changes

| Test file | Change |
| --- | --- |
| `tests/test_cli.py` | Patch `crawler_factory` (not `build_crawler`). **Fixes the red baseline.** |
| `tests/test_architecture.py` | Drop `"selectolax"` from `_FORBIDDEN_PREFIXES`. |
| `tests/domains/crawler/test_engine.py` | Wire `Crawler(config, fetcher=FakeFetcher(...), frontier, results)`. Delete `RealishExtractor` — the FakeFetcher's HTML is real `<a href>` markup, so the real `SelectolaxExtractor` parses it and every assertion still holds. |
| `tests/domains/crawler/stages/test_parse_stage.py` | Drop `FakeExtractor`; feed real HTML anchors through `DefaultParseStage(seed_host=...)`. Keep all five behaviours: normalize/dedup/sort, on-host vs offsite (subdomain excluded), resolve-against-final-url after redirect, non-html → empty, error passthrough. |
| `tests/gateways/parsing/test_selectolax_extractor.py` | **Move** to `tests/domains/crawler/test_extractor.py`. Import from `domains.crawler.extractor`; drop the `LinkExtractor` port assertion; drop the `base_url` argument from every `extract()` call. |
| `tests/domains/crawler/test_ports.py` | Protocol list → `("Fetcher", "Queue")`. |
| `tests/domains/crawler/test_public_surface.py` | Remove `DefaultFetchStage` and `NoOpRobotsPolicy`. |
| `tests/domains/crawler/stages/test_fetch_stage.py` | **Delete.** |
| `tests/domains/crawler/test_robots.py` | **Delete.** |
| `tests/crawler/test_factory.py` | Unchanged (still asserts `crawler_factory` returns a `Crawler`). |
| `tests/e2e/*` | Unchanged (drive the real stack through `crawler_factory`; behaviour identical). |

## README changes

- **Mermaid + prose:** the selectolax extractor moves into `src/domains/crawler`;
  gateways become "httpx fetcher · in-memory queue" only.
- **Ports list:** `Fetcher`, `Queue` (remove `LinkExtractor`, `RobotsPolicy`, and the
  two stage Protocols).
- **Domain purity wording:** change "imports only the standard library" to
  "performs no I/O — it uses selectolax purely for in-process HTML parsing, but makes
  no network or filesystem calls." State the narrowed invariant the architecture test
  now enforces (no httpx/typer/asyncer/gateways/crawler imports in the domain).
- **Data flow:** remove the fetch-stage / robots-gate box; workers call the fetcher
  directly.
- **robots.txt:** reframe from "NoOp placeholder allows every URL" to **future work**:
  not implemented; a real policy must fetch/cache `/robots.txt`, honour Disallow +
  Crawl-delay, and deny on parse failure before running against third-party sites.
- **Directory tree:** fix the already-stale `builder.py` → `factory.py`; remove
  `robots.py`; move the extractor under the domain; update the ports/stages lines.

## Out of scope

- Implementing robots.txt (documented as future work only).
- Changing crawl behaviour, CLI flags, output format, or concurrency model.
- Making `DefaultParseStage.parse` synchronous (it stays `async` to avoid touching
  the engine call site; it does no awaiting, which is acceptable).

## Verification

`make check` (format-check + lint + typecheck + test) must pass and the suite must be
**green** — including the 3 previously-failing `test_cli.py` tests. The
`test_architecture` boundary test must still pass with the narrowed forbidden list.
