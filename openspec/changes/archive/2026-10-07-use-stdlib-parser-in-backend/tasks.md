# Tasks

Paths are relative to `engineer-hiring-tech-exercise/python/backend/`. Run commands from there.

## 1. The parser

- [x] 1.1 Add `StdlibHtmlParser` to `src/crawler_api/adapters.py` (an `html.parser.HTMLParser` subclass created per call that collects the first `<base href>` and every non-blank `<a href>`, including self-closing ones, then joins all links with the base after `close()`; bytes decoded with the Content-Type charset when known, else UTF-8, with `errors="replace"`); add `tests/test_parser.py` porting the library's six parser cases (document order, ignored tags and blank hrefs, malformed HTML, relative and absolute `<base href>`, non-UTF-8 bytes) plus a typed `parser: Parser = StdlibHtmlParser()` check; verify `uv run pytest tests/test_parser.py` and `uv run mypy` pass
- [x] 1.2 Add the differential test to `tests/test_parser.py`: a table of tricky snippets from design.md decision 4, each parsed by both `StdlibHtmlParser` and `DefaultSelectolaxParser` and expected to be identical, with any meaningful difference listed explicitly as an expected difference and a comment explaining it; verify `uv run pytest tests/test_parser.py` passes

## 2. Wiring and docs

- [x] 2.1 Make `CrawlService.start` pass `parser=StdlibHtmlParser()` and remove the `DefaultSelectolaxParser` import from `service.py`; add a service test that a crawl's links come from the new parser (for example a page whose `<base href>` comes after its anchors); update `README.md` ("How it is wired": the parser line; Limitations: the parsing speed trade-off with the measured numbers, and no `<meta charset>` sniffing); verify `uv run ruff check`, `uv run ruff format --check`, `uv run mypy` and `uv run pytest` all pass and `grep -n selectolax src` finds nothing

## 3. Integration check

- [x] 3.1 Run `docker compose up --build --wait` from the repo root, then `bash scripts/docker-smoke.sh`, then a crawl of `https://books.toscrape.com/` with `max_pages` 20 through the dashboard's API, comparing its page and link counts with the same crawl run by the `crawl` CLI (which still uses selectolax); verify the counts match, then stop the stack; also verify the library tests (`uv run pytest` in `python/`) still pass with no changes under `python/src`
