# Proposal

## Why

The crawler library is built around three pluggable components: a fetcher, a parser and a writer. The backend supplies its own fetcher (`SharedClientFetcher`) and writer (`JobWriter`), but still uses the library's selectolax-based parser. Giving the backend its own parser, built on Python's standard-library `html.parser`, completes that picture: every component the service uses is its own. It also shows that the `Parser` protocol doesn't depend on any particular HTML library. The service's page parsing becomes pure Python, which is easier to read, debug and step through.

## What Changes

- Add `StdlibHtmlParser` to `python/backend/src/crawler_api/adapters.py`. It implements the library's `Parser` protocol (`parse(page) -> list[str]`) using `html.parser.HTMLParser`, with no new dependency.
- It extracts links exactly as the current parser does:
  - every non-blank `<a href>`, in document order, with surrounding whitespace trimmed;
  - if the page has a `<base href>`, the first one is applied to every link, as selectolax does, even links that appear before it.
- Page bytes are decoded using the charset from the response's Content-Type, falling back to UTF-8 with replacement characters. Undecodable bytes never crash a crawl.
- `CrawlService` always uses `StdlibHtmlParser` instead of `DefaultSelectolaxParser`.
- **Unchanged:**
  - the `site-crawler` library, its `DefaultSelectolaxParser` and the `crawl` CLI, which keep using selectolax;
  - the API, the dashboard and the Docker setup.
- selectolax stays installed in the backend, because `site-crawler` depends on it. The backend's tests use it as the reference for checking the new parser matches.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Which library parses pages is an implementation detail. The links a crawl reports must stay the same, as `site-crawl` already requires ("Each visited page is reported with all its links", "Links are resolved and normalised"). The change sets `skip_specs: true`.

## Impact

- **Backend code:**
  - `src/crawler_api/adapters.py`: the new parser.
  - `src/crawler_api/service.py`: wiring.
- **Backend tests:** parser unit tests, plus parity tests that run the same HTML through both parsers and expect identical output.
- **Backend docs:** `python/backend/README.md` ("How it is wired" and the limitations).
- **Performance:** `html.parser` is pure Python and slower than selectolax's C-based Lexbor engine. Parsing runs on the event loop, so large pages hold it for longer. The design measures this and records the numbers.
