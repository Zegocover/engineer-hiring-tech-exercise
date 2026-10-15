# Proposal

## Why

`HttpxFetcher` and `SelectolaxParser` are the crawler's built-in fallbacks, but their names don't say so. A planned FastAPI backend will wire up its own adapters and pass them to `Crawler` explicitly. Naming the built-ins as defaults makes it clear that they are what `Crawler` uses when nothing is supplied, not the only implementations.

## What Changes

- **BREAKING**: Rename `HttpxFetcher` to `DefaultHttpxFetcher`.
- **BREAKING**: Rename `SelectolaxParser` to `DefaultSelectolaxParser`.
- Update every import, re-export (`site_crawler`, `site_crawler.fetchers`, `site_crawler.parsers`), the default fallback in `Crawler`, the tests and `python/README.md`.
- No aliases for the old names: the package has no consumers outside this repository yet.
- Module file names (`httpx_fetcher.py`, `selectolax_parser.py`) and behaviour are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The specs describe a default HTTP fetcher and HTML parser without naming classes, so no requirement changes. The change sets `skip_specs: true`.

## Impact

- **Code**: `python/src/site_crawler/fetchers/`, `python/src/site_crawler/parsers/`, `python/src/site_crawler/core/crawler.py`, `python/src/site_crawler/__init__.py`.
- **Tests**: `test_fetchers.py`, `test_parsers.py`, `test_end_to_end.py`, `test_package.py` (public API list).
- **Docs**: `python/README.md` (extension section and package layout tree).
- **Public API**: the two old names disappear from `site_crawler.__all__`. Archived OpenSpec changes keep the old names as historical record.
