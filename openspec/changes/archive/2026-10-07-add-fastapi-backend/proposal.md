# Proposal

## Why

The crawler is only reachable through the `crawl` command, which runs one crawl per process and prints to standard output. The exercise asks how the design would extend to crawling several sites at once and suggests that a command line may not be the best interface for that. An HTTP backend lets clients start, watch and cancel many crawls in one long-running process. It also shows that the library's extension points work: the backend wires up its own fetcher and writer instead of relying on the library's defaults.

## What Changes

- Add a new FastAPI application in a sibling uv project, `engineer-hiring-tech-exercise/backend/`, that depends on the `site-crawler` library by path.
- Expose a job-based crawl API:
  - `POST /crawls` starts a crawl in the background and returns its id immediately.
  - `GET /crawls` lists crawls.
  - `GET /crawls/{id}` returns the crawl's full details, including its effective limits.
  - `GET /crawls/{id}/status` returns a lightweight status and statistics for polling.
  - `GET /crawls/{id}/pages` returns the pages found so far, paginated.
  - `GET /crawls/{id}/links` returns every distinct link found so far across all pages, paginated.
  - `DELETE /crawls/{id}` cancels a running crawl.
  - `GET /health` reports liveness.
- Run several crawls concurrently in one process, each following the same rules as the `crawl` command (single host, de-duplication, normalisation, robots.txt).
- Enforce server-side limits on each crawl's page budget and concurrency so one request cannot run an unbounded crawl.
- Keep jobs and results in memory, behind a store interface so a persistent store could replace it later.
- Add backend-specific adapters:
  - A fetcher that shares one HTTP connection pool across all crawls and leaves closing it to the application.
  - A writer that records each page into the crawl's job.
  - The parser is the library's default, passed in explicitly.
- Add a CI job for the backend (lint, format, type-check, tests) alongside the existing library job.
- The `site-crawler` library and the `crawl` command are unchanged.

## Capabilities

### New Capabilities

- `crawl-api`: an HTTP interface for starting, monitoring, paging through the pages and links of, and cancelling crawls, with several crawls running at once.

### Modified Capabilities

None. The backend uses the existing `crawler-extension-api` as specified, and each crawl follows `site-crawl` unchanged.

## Impact

- **New code**: `backend/` (its own `pyproject.toml`, `uv.lock`, `src/`, `tests/`, `README.md`).
- **Dependencies (backend only)**: `fastapi`, `uvicorn`, `httpx`, and `site-crawler` as a path dependency. The library gains no dependencies.
- **CI**: `.github/workflows/ci.yml` gains a backend job.
- **Docs**: a backend README with run instructions and API examples, plus a pointer from `python/README.md`.
- **Operational**: crawl results live in process memory and are lost on restart. The API has no authentication and is intended for local or trusted use (see design.md).
