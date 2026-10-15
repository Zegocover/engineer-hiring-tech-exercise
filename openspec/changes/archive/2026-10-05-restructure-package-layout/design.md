# Design

## Context

See proposal.md for the motivation. The current package (`python/src/site_crawler/`) has 10 flat modules. `interfaces.py` holds both the three Protocols and the data classes `FetchResult`, `PageResult` and `FetchError`; `CrawlConfig` lives in `config.py` and `CrawlStats` in `manager.py`. The tests (101) and `examples/custom_writer.py` import from these module paths, and the README lists the flat tree. The behaviour contracts are in `openspec/specs/site-crawl` and `openspec/specs/crawler-extension-api`, and must not change.

## Goals / Non-Goals

**Goals:**
- One folder per layer: what consumers implement (`interfaces/`), what flows between components (`models/`), the shipped defaults (`fetchers/`, `parsers/`, `writers/`) and the engine (`core/`).
- A dependency direction that can be read from the tree, with no import cycles.
- An unchanged top-level public API.

**Non-Goals:**
- Any behaviour, signature or output change.
- Restructuring `tests/` to mirror the package (the tests stay flat; only their imports change).
- Compatibility shims for old module paths.

## Decisions

### D1. Target layout

```
site_crawler/
  __init__.py              # public API: re-exports everything below a consumer needs
  cli.py                   # unchanged location (entry point site_crawler.cli:main)
  interfaces/
    __init__.py            # Fetcher, Parser, Writer
    fetcher.py             # Fetcher
    parser.py              # Parser
    writer.py              # Writer
  models/
    __init__.py            # FetchResult, PageResult, CrawlConfig, ConfigError, CrawlStats, FetchError
    fetch.py               # FetchResult
    page.py                # PageResult
    config.py              # CrawlConfig, ConfigError, DEFAULT_USER_AGENT
    stats.py               # CrawlStats
    errors.py              # FetchError
  fetchers/
    __init__.py            # HttpxFetcher
    httpx_fetcher.py
  parsers/
    __init__.py            # SelectolaxParser
    selectolax_parser.py
  writers/
    __init__.py            # TextWriter, JsonLinesWriter
    text.py
    jsonl.py
  core/
    __init__.py            # Crawler
    crawler.py             # Crawler (was manager.py)
    urls.py
    robots.py
```

- `manager.py` is renamed to `core/crawler.py` to match the class it holds. `CrawlStats` moves out to `models/stats.py`, since it's returned data, not engine logic.
- `FetchError` goes in `models/errors.py`. It's part of the fetcher contract, but it's a value type that fetchers raise and the engine catches, so it sits with the data rather than the protocols. `interfaces/fetcher.py` imports it for its docstring and type references.
- `CrawlConfig` counts as a model: it's an immutable, validated data object passed into the engine.
- **Alternative considered:** a single `implementations/` folder for the defaults. Rejected: grouping by role (`fetchers/`, `parsers/`, `writers/`) gives each future component, such as a `writers/sql.py`, an obvious home and mirrors the three interfaces.

### D2. Dependency direction

```
models  <--  interfaces  <--  fetchers / parsers / writers  <--  core  <--  cli, __init__
```
- `models` imports nothing from the package.
- `interfaces` imports only `models`.
- The default implementations import `models` (and `interfaces` only for typing, if at all).
- `core` imports all of the above (it builds the defaults when none are supplied).
- `cli` and the package `__init__` import from `core`, `models` and `writers`.

No layer imports a layer to its right, so no import cycles are possible. This is verified by importing each subpackage on its own in a test (see tasks).

### D3. Sub-package `__init__` files re-export their contents

Each sub-package `__init__.py` re-exports its public names with `__all__`, so internal code can write `from site_crawler.models import FetchResult` without knowing the file. Internal modules import from sibling *sub-packages* (e.g. `from site_crawler.models import ...`), never from the top-level `site_crawler`, which would create cycles via `__init__`.

### D4. Top-level public API

`site_crawler/__init__.py` keeps every current export:
- `Crawler`, `CrawlConfig`, `CrawlStats`, `ConfigError`
- `Fetcher`, `Parser`, `Writer`
- `FetchResult`, `PageResult`, `FetchError`

It also adds the defaults: `HttpxFetcher`, `SelectolaxParser`, `TextWriter`, `JsonLinesWriter`. Consumers who customise one component often need the others, and today they must import those from internal modules.

### D5. No shims; move with `git mv`

Old paths aren't kept (user decision: nothing is released). Tests, examples and the README are updated in the same change. Files are moved with `git mv` so history follows them. That requires the current code to be committed first; it's currently untracked.

## Risks / Trade-offs

- [Import cycles appear through `__init__` re-exports] → keep the D2 direction, and add a test that imports every subpackage in a fresh interpreter.
- [A missed import breaks only at runtime] → mypy `--strict` over `src`, `tests` and `examples`, plus the full test suite, plus a CLI smoke run, catch unresolved imports.
- [Untracked files mean `git mv` can't preserve history] → commit the current state before starting (task 1.1). If that's skipped, a plain move still works, but reviewers lose the rename diff.
- [More files and folders for a small package] → accepted. The layering is the point of the exercise, and each folder has an obvious growth path.
