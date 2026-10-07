# Tasks

Each rename updates every importer of the class in the same task: importing any `site_crawler` subpackage first runs `site_crawler/__init__.py`, which imports `core/crawler.py`, so a half-renamed package cannot be imported at all.

## 1. Rename the default fetcher

- [x] 1.1 Rename `HttpxFetcher` to `DefaultHttpxFetcher` in `fetchers/httpx_fetcher.py`, `fetchers/__init__.py` (re-export and `__all__`), `core/crawler.py` (import, default fallback, docstring) and `site_crawler/__init__.py` (import and `__all__`); verify `uv run python -c "from site_crawler.fetchers import DefaultHttpxFetcher"` succeeds
- [x] 1.2 Update `tests/test_fetchers.py`, `tests/test_end_to_end.py` and the `PUBLIC_API` set in `tests/test_package.py` to use `DefaultHttpxFetcher`; verify `uv run pytest tests/test_fetchers.py tests/test_end_to_end.py` passes

## 2. Rename the default parser

- [x] 2.1 Rename `SelectolaxParser` to `DefaultSelectolaxParser` in `parsers/selectolax_parser.py`, `parsers/__init__.py` (re-export and `__all__`), `core/crawler.py` (import, default fallback, docstring) and `site_crawler/__init__.py` (import and `__all__`); verify `uv run python -c "from site_crawler.parsers import DefaultSelectolaxParser"` succeeds
- [x] 2.2 Update `tests/test_parsers.py` and the `PUBLIC_API` set in `tests/test_package.py` to use `DefaultSelectolaxParser`; verify `uv run pytest tests/test_parsers.py tests/test_package.py tests/test_defaults.py` passes

## 3. Documentation

- [x] 3.1 Update `python/README.md` (the defaults paragraph in the extension section and the package layout tree); verify `grep -rnw "HttpxFetcher\|SelectolaxParser" python/src python/tests python/examples python/README.md` returns no matches

## 4. Integration check

- [x] 4.1 Run the full CI suite from `python/`: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy` and `uv run pytest`; verify all pass
