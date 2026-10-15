# Proposal

## Why

The crawl API can only be used with curl or the generated `/docs` page, which makes the backend hard to demonstrate and the crawl results hard to read. A small web dashboard lets someone start a crawl, watch it progress, browse the pages and links it finds, and cancel it. It completes the "UI, then API, then crawler" picture the library README sketches for scaling beyond the CLI.

## What Changes

- Add a Next.js (App Router, TypeScript) application in `front-end/`.
- **Route handlers as the browser's API.** The dashboard's server exposes `/api/crawls...` route handlers that call the FastAPI backend from the server, using a server-only `CRAWLER_API_URL` setting. The browser never contacts FastAPI directly, so there's no CORS setup and the backend's address is never exposed to the client. The handlers pass the backend's status codes and error details through, and report the backend being unreachable as a clear error.
- **Screens:**
  - A form to start a crawl (URL, page budget, depth, concurrency, robots.txt), showing validation errors returned by the API.
  - A list of crawls, newest first, with status and statistics.
  - A crawl view that polls status while the crawl is running and stops polling once it finishes. It shows statistics and any error, has paged tabs for the pages found (with their links) and for the distinct links, and a cancel button while running.
- **Typed API contract.** TypeScript types are generated from the backend's OpenAPI schema and committed, with a script to regenerate them, so the dashboard can't silently drift from the API.
- **Tests:** component and route-handler tests with the API mocked, including polling stopping, cancel, pagination and error display.
- **CI:** a `front-end` job (install, lint, type-check, test, build).
- **README:** keep the existing front-end brief and add a "Solution" section. It should state plainly that this app is the dashboard for the Python crawler's API, not a solution to the front-end exercise, and cover how to run it alongside the backend.

## Capabilities

### New Capabilities

- `crawl-dashboard`: a web UI for starting, monitoring, browsing and cancelling crawls through the crawl API, including how it reaches the API and how it reports API errors and an unreachable backend.

### Modified Capabilities

None. The dashboard uses the existing `crawl-api` endpoints as specified. Because requests go through the dashboard's own server, the API needs no CORS or other changes.

## Impact

- **New code**: `front-end/` (Next.js app, `package.json`, lockfile, tests). `front-end/README.md` is extended, not replaced.
- **Dependencies (front end only)**: Next.js, React, a data-fetching library for polling and pagination, an OpenAPI-to-TypeScript generator, and test tooling. The Python projects gain nothing.
- **CI**: `.github/workflows/ci.yml` gains a `front-end` job.
- **Running locally**: two processes, the FastAPI backend from `python/backend` and the dashboard from `front-end`, connected by `CRAWLER_API_URL`.
- **Depends on**: `move-backend-into-python`, which should land first so the docs and the default `CRAWLER_API_URL` setup describe the final layout.
