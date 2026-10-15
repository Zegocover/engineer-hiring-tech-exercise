# Tasks

All paths are relative to `engineer-hiring-tech-exercise/python/`.

## 1. Project setup

- [x] 1.1 Create `pyproject.toml` (src layout, package `site_crawler`, Python >=3.12, runtime deps httpx and selectolax, dev deps pytest, pytest-asyncio, respx, ruff, mypy; `crawl` console script) and verify `uv sync` succeeds and `uv run python -c "import site_crawler"` works
- [x] 1.2 Configure ruff, mypy `--strict` and pytest (asyncio mode auto) in `pyproject.toml`, add `.pre-commit-config.yaml` and `.gitignore`, and verify `uv run ruff check`, `uv run mypy src` and `uv run pytest` all run cleanly on the empty package
- [x] 1.3 Add `.github/workflows/ci.yml` running ruff, mypy and pytest on Python 3.12 and 3.13, and verify the workflow YAML validates (e.g. `actionlint` or a push to a branch)

## 2. Public types and URL handling

- [x] 2.1 Implement `interfaces.py` (`FetchResult`, `PageResult`, `FetchError`, `Fetcher`/`Parser`/`Writer` Protocols) and `config.py` (`CrawlConfig` with validation of the base URL and limits), with unit tests verifying an invalid base URL (`example.com`, `ftp://...`) raises and a plain class satisfies each Protocol under mypy
- [x] 2.2 Implement `urls.py` (`resolve`, `normalise`, `is_http`, `same_host`) per design D4, with parametrised tests covering the site-crawl normalisation, non-HTTP and subdomain/`www.` scenarios
- [x] 2.3 Re-export the public API from `site_crawler/__init__.py` and verify `from site_crawler import Crawler, CrawlConfig, Fetcher, Parser, Writer, FetchError` works in a test

## 3. Crawl manager

- [x] 3.1 Implement `Crawler` in `manager.py` with the private frontier (`_queue`, `_seen`, `_enqueue` with depth and page budget), N workers, a single writer task, and a stats summary, per design D5/D6. Verify with fake fetcher/parser/writer tests covering: cyclic links fetched once, per-page link de-duplication in document order, off-host links reported but not fetched, the empty-links page, `max_pages` and `max_depth`
- [x] 3.2 Add redirect handling (resolve against `final_url`, drop pages whose final URL is off-host) and the non-HTML rule, with tests for the redirect, off-host redirect and PDF scenarios
- [x] 3.3 Implement the error policy from design D7: `FetchError` counted and the crawl continues, other exceptions cancel the work, close the writer and fetcher, and re-raise. Test the "one page returns 500", "parser bug" and writer-closed-exactly-once scenarios, plus a test that a failing worker never leaves `run()` hanging (use `asyncio.wait_for`)
- [x] 3.4 Implement `robots.py` (fetch via the configured fetcher, allow-all on 4xx/`FetchError`, `urllib.robotparser`) and wire it into `_enqueue` behind `CrawlConfig.respect_robots`. Test the disallowed-path (reported but not fetched) and robots-disabled scenarios

## 4. Default components

- [x] 4.1 Implement `HttpxFetcher` (shared `AsyncClient`, connection limits matching concurrency, timeout, body size cap, retries with backoff for timeout/connection/429/5xx, `FetchError` on final failure) with respx tests for success, redirect `final_url`, 503-then-200 recovery, persistent 500 to `FetchError`, and timeout
- [x] 4.2 Implement `SelectolaxParser` (`<a href>` in document order, `<base href>` join, skip empty hrefs) with tests against HTML fixtures, including malformed HTML and a `<base>` tag
- [x] 4.3 Implement `TextWriter` and `JsonLinesWriter` (writing to an injectable stream, flush on `aclose`), with tests verifying the text layout and that every JSON Lines line parses with `url` and `links` keys
- [x] 4.4 Make `Crawler` default to `HttpxFetcher`, `SelectolaxParser` and `TextWriter` when no components are passed, and verify with a respx-backed test that a defaults-only crawl of a fake site writes the expected text output

## 5. CLI

- [x] 5.1 Implement `cli.py` (argparse options per design D10, logging to stderr, summary to stderr, exit codes: 0 on success, non-zero on invalid URL or base URL failure) and verify with tests calling `main([...])` against a respx-mocked site, checking stdout, stderr and exit status
- [x] 5.2 Smoke-test the installed script with `uv run crawl https://example.com --max-pages 5` and `--format jsonl`, and verify the output matches the spec layouts

## 6. Integration and documentation

- [x] 6.1 Add an end-to-end test that crawls a respx-mocked site (about 10 pages with a cycle, a redirect, an off-host redirect, a PDF, an external link, a 500 page and a robots-disallowed path) and asserts the exact set of reported pages, links and the summary counts
- [x] 6.2 Add a consumer-extension example (`examples/custom_writer.py` with a plain-class writer collecting results) plus a test that runs it, verifying the extension API works without subclassing
- [x] 6.3 Extend `README.md` with: install/usage, architecture diagram and design decisions D1–D11 with trade-offs, recorded assumptions (`<a href>` only, `www.` is a separate host, http/https as one site, robots default), the scale-out design (datastore, webserver, visualiser, shared frontier, multi-domain), IDE and AI tool usage, and future work. Verify every command in the README runs as written
- [x] 6.4 Run `uv run ruff check`, `uv run mypy src` and `uv run pytest` and verify all pass with no warnings
