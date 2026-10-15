# Design

## Context

Greenfield. The exercise repo (`engineer-hiring-tech-exercise/`, its own git repo) has only READMEs; code goes in `engineer-hiring-tech-exercise/python/`. Python 3.13 is available locally. Constraints from the brief: no Scrapy or Playwright; libraries are allowed for HTTP and HTML parsing; it must be fast without wasting accuracy or compute; it must be structured as a production project; and the README must explain design choices and AI tool usage. See proposal.md for motivation, and specs/ for required behaviour.

Our design diagram (Zego.drawio.svg) shows a `CrawlerManager` that uses Request, Parse and Store components, a request queue, and a downstream datastore, webserver and visualiser. This change builds the manager, the three components and the CLI. The rest stays a README note.

## Goals / Non-Goals

**Goals:**
- A small, typed public API: `Crawler`, `CrawlConfig`, three component protocols, result types and a `FetchError`.
- Crawl correctness lives in one place (the manager) and does not depend on consumer code.
- High throughput on I/O-bound crawling, with bounded memory and open sockets.
- Fast, deterministic tests with no network access.

**Non-Goals:**
- Pluggable frontier or distributed crawling. The frontier is private manager state.
- JavaScript rendering, sitemap discovery, `<link>`/`<img>`/`<script>` extraction.
- Persisting results anywhere other than stdout.
- Plugin discovery via entry points. The CLI only uses the defaults; consumers wire custom components in code.

## Decisions

### D1. Package layout

```
python/
  pyproject.toml
  src/site_crawler/
    __init__.py        # public re-exports
    interfaces.py      # Protocols, FetchResult, PageResult, FetchError
    config.py          # CrawlConfig dataclass
    urls.py            # normalise(), resolve(), is_same_host()
    manager.py         # Crawler: frontier, workers, writer task, stats
    robots.py          # robots.txt gate
    fetchers.py        # HttpxFetcher (default)
    parsers.py         # SelectolaxParser (default)
    writers.py         # TextWriter, JsonLinesWriter (default: text)
    cli.py             # argparse -> CrawlConfig -> Crawler
  tests/
```
`src/` layout so tests run against the installed package, not the working directory.

### D2. Component interfaces are `typing.Protocol`

```
Fetcher:  async fetch(url) -> FetchResult      ; async aclose()
Parser:   parse(page: FetchResult) -> list[str]   (raw hrefs)
Writer:   async write(result: PageResult)       ; async aclose()
```
- **Why:** structural typing means consumers don't import or subclass package types (spec: "no package inheritance"). Fakes in tests are plain classes. `mypy` still checks conformance where they're wired up.
- **Alternative:** ABCs. They give an error when the object is created if a method is missing, but force inheritance. Rejected for that coupling.
- `Parser` is synchronous: parsing is fast and CPU-bound, and making it async gains nothing. If a slow consumer parser becomes an issue, the manager can wrap it in `asyncio.to_thread` without changing the interface.
- `FetchResult.final_url` exists so relative links resolve correctly after redirects.

### D3. The parser returns raw strings; the manager owns URL handling

The flow is: parser output, then `resolve(final_url, base_href)`, then `normalise`, then dropping non-http(s) links, then de-duplicating per page, which gives the reported links. Those are then filtered by the same-host check, robots and limits before being enqueued.
- **Why:** consumer bugs can only affect which links are extracted, never scope or de-duplication (spec: custom parser).
- `<base href>` is the one exception, because only the parser sees the DOM. *Decision:* a parser joins hrefs with `<base href>` when one is present, and returns them raw otherwise. The manager always applies `urljoin(final_url, href)`, which leaves already-absolute URLs unchanged, so both cases work.

### D4. Normalisation rules (`urls.py`)

- Lowercase scheme and host.
- Drop the default port (`:80` for http, `:443` for https).
- Remove the fragment.
- An empty path becomes `/`.
- Keep the query string unchanged.
- Do **not** strip trailing slashes or sort query parameters. Either can change which resource is served, and over-normalising silently loses pages.

Same-host means equality of the normalised `hostname` plus port (after dropping defaults). Scheme is ignored, so `http://example.com` links are in scope for an `https://example.com` crawl. **Assumption:** this treats http and https as the same site. It's noted in the README.

### D5. Concurrency: N identical workers plus 1 writer task

```
            +------------------- Crawler.run() --------------------+
 seed  -->  | _enqueue --> asyncio.Queue[(url, depth)] --+         |
            |     ^                                      v         |
            |     |        worker x N:  fetch -> parse -> links    |
            |     +---------- same-host & limits <------+  |       |
            |                                              v       |
            |                    asyncio.Queue[PageResult]         |
            |                                 |                    |
            |                                 v                    |
            |                    writer task (1): writer.write()   |
            +------------------------------------------------------+
```
- Workers loop on `queue.get()` and call `task_done()` in `finally` so `queue.join()` can't hang on a failure.
- `run()` waits on `queue.join()`, then cancels the workers, sends a sentinel to the writer queue, waits for the writer task, and calls `writer.aclose()` then `fetcher.aclose()`. The closing happens in `finally`, so it also runs when an error is propagated.
- **Why one writer:** results are delivered one at a time and in order with no interleaving (specs), and a consumer writer needs no locking.
- **Alternative (from the diagram):** separate parse/request/write worker pools. Rejected because the extra queue hand-offs add latency and complexity, and parsing is too cheap to need its own pool. The diagram's three *roles* map to the three Protocols instead.
- Default concurrency is 16. `httpx.AsyncClient` connection limits are set to match, so concurrency is bounded at the socket level too.

### D6. Frontier is private manager state

`_queue: asyncio.Queue[tuple[str, int]]` and `_seen: set[str]`. `_enqueue` checks `_seen`, the depth limit and the page budget, then adds to `_seen` and calls `put_nowait`, all with no `await` in between, so the check-and-insert can't be interleaved on the single-threaded event loop. Marking a URL as seen when it's queued, rather than when it's fetched, prevents duplicate in-flight fetches.
- `max_pages` is counted when a URL is queued, so the limit is exact and no fetches are wasted.
- The queue is unbounded. The number of entries can't exceed the number of unique URLs, which `_seen` holds anyway.
- **Extension path:** extract a `Frontier` Protocol later if distributed crawling is needed (README note).

### D7. Error policy

- `FetchError` (raised by fetchers for network errors, timeouts and HTTP error statuses after retries) is logged at warning level and counted in `stats.errors`, and the crawl continues.
- Any other exception from a component is propagated: the remaining work is cancelled, closing still runs, and the exception is re-raised from `run()`. This exposes consumer bugs instead of producing partial output that looks complete.
- Retries live in `HttpxFetcher`: up to 2 retries with exponential backoff and jitter for timeouts, connection errors, 429 and 5xx, honouring `Retry-After` up to a cap. This is the fetcher's job because it's protocol-specific.
- The CLI exits non-zero if the base URL failed (stats show the seed failed) or the config is invalid.

### D8. Default libraries

- **httpx** (`AsyncClient`, `follow_redirects=True`, HTTP/2 optional via the `h2` extra). Its API is mature and typed, and **respx** makes testing straightforward. Alternative: aiohttp, which is slightly faster but has weaker typing and test tooling.
- **selectolax** (Lexbor backend) for parsing. It's many times faster than BeautifulSoup and handles malformed HTML. Alternative: BeautifulSoup with lxml, which is slower and heavier.
- Non-HTML responses are detected from the `Content-Type` header. The fetcher downloads bodies only for textual types (`text/*`, XHTML/XML/JSON, or a missing content type), capped at 10 MB to bound memory. Binary resources (PDFs, images) are not downloaded. *(Revised during implementation: skipping all non-HTML bodies also emptied `text/plain` robots.txt, which the end-to-end test caught.)*

### D9. robots.txt

The manager fetches `/robots.txt` through the configured fetcher before seeding. If it gets a 4xx response or a `FetchError`, it allows everything. It parses with stdlib `urllib.robotparser` and uses the configured user agent. Disallowed URLs are filtered when queued but are still reported as links (spec). `Crawl-delay` is ignored, as noted in the README.

### D10. CLI

`crawl URL [--concurrency N] [--max-pages N] [--max-depth N] [--timeout S] [--no-robots] [--format text|jsonl] [--user-agent S] [-v]`. It uses argparse, which is stdlib and enough here. Results go to stdout; logs and the summary go to stderr. `asyncio.run(main())`. Exposed via `[project.scripts] crawl = "site_crawler.cli:main"`.

### D11. Tooling

uv for env and lockfile; pytest, pytest-asyncio and respx; ruff (lint and format); mypy `--strict`; a GitHub Actions workflow running ruff, mypy and pytest on 3.12 and 3.13; pre-commit hooks.

## Risks / Trade-offs

- [Large sites use unbounded memory for `_seen`] → `--max-pages` caps it. A Bloom filter or external store is noted in the README as the scale-out path.
- [Parsing on the event loop blocks workers on huge pages] → selectolax is fast and bodies are size-capped. `to_thread` is a drop-in fix if profiling shows a problem.
- [Treating http and https as one host could crawl duplicate content] → only when a site serves both; documented assumption.
- [Not normalising trailing slashes may fetch `/a` and `/a/` separately] → chosen for accuracy over fewer requests; documented.
- [robots.txt fetched through the consumer fetcher could fail strangely with a custom fetcher] → any non-`FetchError` exception there is treated like other component errors (propagated), so behaviour is consistent.
- [Hammering small sites with concurrency 16] → configurable. A per-host politeness delay is a README follow-up.
