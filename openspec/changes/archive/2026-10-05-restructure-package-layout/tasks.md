# Tasks

All paths are relative to `engineer-hiring-tech-exercise/python/`. After every task, run `uv run ruff check`, `uv run ruff format --check`, `uv run mypy` and `uv run pytest` and verify they pass with the same 101+ tests green. The suite stays green throughout because each group updates its importers in the same task.

## 1. Baseline

- [x] 1.1 Confirm the current crawler code is committed in the git repo (ask the user to commit it if it is still untracked, so moves can use `git mv`) and verify the baseline checks pass

## 2. Models

- [x] 2.1 Create `src/site_crawler/models/` with `fetch.py` (`FetchResult`), `page.py` (`PageResult`), `errors.py` (`FetchError`), `config.py` (`CrawlConfig`, `ConfigError`, `DEFAULT_USER_AGENT`, moved from `config.py`), `stats.py` (`CrawlStats`, moved from `manager.py`) and an `__init__.py` re-exporting them. Remove the old `config.py`, update all importers in `src`, `tests` and `examples`, and verify the checks pass

## 3. Interfaces

- [x] 3.1 Replace `interfaces.py` with an `interfaces/` package (`fetcher.py`, `parser.py`, `writer.py`, and an `__init__.py` re-exporting `Fetcher`, `Parser` and `Writer`) that imports its types from `site_crawler.models`, update all importers, and verify the checks pass, including mypy's structural check in `tests/test_interfaces.py`

## 4. Default implementations

- [x] 4.1 Move `fetchers.py` to `fetchers/httpx_fetcher.py`, `parsers.py` to `parsers/selectolax_parser.py`, and `writers.py` to `writers/text.py` and `writers/jsonl.py`, each package with a re-exporting `__init__.py`. Update importers (including `respx`/test references) and verify the checks pass

## 5. Core

- [x] 5.1 Move `manager.py` to `core/crawler.py`, and `urls.py` and `robots.py` into `core/`, with `core/__init__.py` exporting `Crawler`. Update importers (the CLI and tests) and verify the checks pass and `uv run crawl https://books.toscrape.com/ --max-pages 5` produces the same output shape as before

## 6. Public API, layering guard and docs

- [x] 6.1 Update `site_crawler/__init__.py` to export the existing names plus `HttpxFetcher`, `SelectolaxParser`, `TextWriter` and `JsonLinesWriter`, and extend `tests/test_package.py` to assert the full `__all__` and that each name is importable from the package root
- [x] 6.2 Add a test that imports each subpackage (`models`, `interfaces`, `fetchers`, `parsers`, `writers`, `core`) in a fresh interpreter (`subprocess` with `sys.executable -c "import ..."`), and a test asserting `site_crawler.models` doesn't import any other `site_crawler` subpackage. Verify both pass
- [x] 6.3 Update `README.md`: replace the package tree with the new layout, fix module references (e.g. the architecture notes and `examples` text), and add a short note on the layering (`models <- interfaces <- defaults <- core`). Verify every command in the README still runs as written
- [x] 6.4 Final verification: run all checks, run `uv run crawl https://books.toscrape.com/ --max-pages 20` and `uv run python -m examples.custom_writer https://books.toscrape.com/ 20`, and confirm `git status` shows the old modules as renames/deletions with no stray files left behind
