# Proposal

## Why

`site_crawler` is a flat set of modules, and `interfaces.py` mixes the extension protocols with the data classes that flow through them. A reader (or a reviewer of the exercise) can't see the package's layers at a glance: what a consumer implements, what data is exchanged, which components are defaults, and which code is the crawl engine. Splitting these into folders makes the extension points and the data models obvious, and gives future components (e.g. a database writer) a clear home.

## What Changes

- Split `interfaces.py` into an `interfaces/` package, with one module per protocol: `Fetcher`, `Parser`, `Writer`.
- Move the data models into a `models/` package: `FetchResult`, `PageResult`, `CrawlConfig` and `ConfigError`, `CrawlStats`, and `FetchError`.
- Group the default implementations by role: `fetchers/` (`HttpxFetcher`), `parsers/` (`SelectolaxParser`), `writers/` (`TextWriter`, `JsonLinesWriter`).
- Move the crawl engine into `core/`: the `Crawler` (formerly `manager.py`), URL handling and the robots.txt gate.
- Keep the top-level `from site_crawler import ...` API unchanged, and export the default implementations there too.
- **BREAKING (internal paths only):** old module paths (`site_crawler.manager`, `site_crawler.config`, `site_crawler.interfaces.<name>` as a flat module, `site_crawler.fetchers`, etc.) are not kept as shims. Nothing has been released, and tests, examples and docs are updated in the same change.
- No behaviour changes: the CLI, its output and every existing test keep the same results.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none). This is a structural refactor; the `site-crawl` and `crawler-extension-api` requirements are unchanged, so the change declares `skip_specs: true`.

## Impact

- **Code:** every module under `engineer-hiring-tech-exercise/python/src/site_crawler/` moves; imports in `tests/` and `examples/` are updated.
- **Docs:** the package tree and file references in `python/README.md` are updated.
- **Public API:** unchanged for `from site_crawler import ...` (adds exports for the default implementations).
- **Dependencies, CLI entry point (`site_crawler.cli:main`), CI:** unchanged.
