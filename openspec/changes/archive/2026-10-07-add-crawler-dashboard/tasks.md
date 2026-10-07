# Tasks

Paths are relative to `engineer-hiring-tech-exercise/`. Run npm commands from `front-end/`.

## 1. Scaffold the app

- [x] 1.1 Generate a Next.js app with `create-next-app` (TypeScript, ESLint, Tailwind, App Router, `src/`, npm) in a temporary directory and move it into `front-end/`, keeping the existing `front-end/README.md` and dropping the generated one; verify `npm ci`, `npm run lint` and `npm run build` succeed and `git diff front-end/README.md` is empty
- [x] 1.2 Add Vitest, React Testing Library, jsdom, MSW and TanStack Query; add `vitest.config.mts`, `vitest.setup.ts` and a `test` script; add one smoke test rendering the home page; verify `npm test -- --run` passes

## 2. API contract

- [x] 2.1 Write `scripts/gen-api.mjs` (spawn `uv run --project ../python/backend python -c ...` to dump `create_app().openapi()`, write `src/lib/api/openapi.json`, then generate `src/lib/api/schema.d.ts` with `openapi-typescript`) and add a `gen:api` script; run it and commit the outputs; verify that running it twice leaves `git diff --exit-code src/lib/api` clean
- [x] 2.2 Add `src/lib/api/types.ts` (aliases for `CrawlRequest`, `CrawlSummary`, `CrawlDetail`, `CrawlStatus`, `PageList`, `LinkList` and `ValidationError`, plus an `ErrorBody` of `{detail: string | ValidationError[]}`) and `src/lib/polling.ts`; verify `npx tsc --noEmit` passes

## 3. Route handlers

- [x] 3.1 Implement `src/lib/backend.ts` (`server-only`): `forward(request, path)` builds the URL from `CRAWLER_API_URL` (default `http://localhost:8000`), copies the method, query string and JSON body, applies a 10 s timeout, returns the backend's status and body unchanged, and maps network errors and timeouts to 502 `{"detail": "Crawler API is unreachable"}`; add node-environment tests with MSW covering pass-through of 200/202/404/409/422, query and body forwarding, the configured address, connection refusal and timeout; verify `npm test -- --run` passes
- [x] 3.2 Add the five route handler files under `src/app/api/crawls/` (list and start; detail and cancel; status; pages; links), awaiting `params` and `encodeURIComponent`-escaping ids; add tests that call each exported handler with a `Request`, and a test that a path outside them (for example `/api/health`) isn't routed; verify `npm test -- --run` and `npm run build` pass, and that the build output lists exactly these API routes

## 4. Client and shared components

- [x] 4.1 Implement `src/lib/client.ts` (typed wrappers for the seven operations against `window.location.origin`, throwing `ApiError {status, detail}` for responses that aren't 2xx), `src/app/providers.tsx` (QueryClient with no retries on 4xx and one retry otherwise) wired into `layout.tsx`, and the `MSW` handlers and fixtures in `src/test/`; add unit tests for `ApiError` with both `detail` shapes; verify `npm test -- --run` passes
- [x] 4.2 Implement `StatusBadge`, `Paginator` (range label, previous and next disabled at the ends) and `ApiErrorNotice` (502 unreachable message, 404 not found with a link back, string detail otherwise); add component tests for each; verify `npm test -- --run` passes

## 5. Screens

- [x] 5.1 Implement `StartCrawlForm` (URL required; optional limits sent only when filled; robots checkbox on by default; submit disabled while pending; 422 errors mapped to fields by `loc[1]`, otherwise to the top of the form; entered values kept; navigate to `/crawls/{id}` on success); add tests for the spec's start scenarios and both rejection scenarios; verify `npm test -- --run` passes
- [x] 5.2 Implement `CrawlList` and the `/` page (newest first; URL, status, pages and errors; links to each crawl; empty state; refresh while any crawl is running or the last fetch failed; unreachable notice); add tests for the listing, refresh while running, the empty state, and the 502-then-recovery scenario; verify `npm test -- --run` passes
- [x] 5.3 Implement `CrawlView` and `/crawls/[id]` (detail and status with `aria-live` stats; status polling that stops when the crawl isn't running; failed error shown; not-found state) plus `PagesTab` and `LinksTab` (page size 50, `keepPreviousData`, refresh while running); add tests for live progress, polling stopping (no further status requests), failed crawl, unknown crawl, next page of pages, and the links tab; verify `npm test -- --run` passes
- [x] 5.4 Add cancel to `CrawlView` (shown only while running; on 200 show `cancelled` and stop polling with pages still browsable; on 409 refetch and show the real status); add tests for the three cancel scenarios; verify `npm test -- --run` passes

## 6. Documentation and CI

- [x] 6.1 Append a "Solution: crawler dashboard" section to `front-end/README.md` below the untouched brief. It should open by saying this is the dashboard for the Python crawler's API, not the front-end exercise, and cover the architecture (browser to route handlers to crawl API), running both servers, `CRAWLER_API_URL`, `gen:api`, testing, an end-to-end test strategy (how Playwright would be added and kept from being brittle) and limitations. Add a pointer to it from `python/backend/README.md`; verify the brief above the new section is byte-for-byte unchanged (`git diff` shows only additions after it)
- [x] 6.2 Add a `front-end` job to `.github/workflows/ci.yml` (Node 24, npm cache, `npm ci`, lint, `tsc --noEmit`, `npm test -- --run`, `npm run build`, then `setup-uv`, `npm run gen:api` and `git diff --exit-code src/lib/api`); verify the workflow parses and that the same commands pass locally

## 7. Integration check

- [x] 7.1 Run the backend (`python/backend`, port 8000) and the dashboard (`npm run dev`), then start a small crawl from the UI, watch it complete, page through the pages and links, cancel a larger crawl, stop the backend and confirm the unreachable notice, and restart it and confirm recovery; also check with the browser's network log or the dev server log that the browser only called `/api/...`; verify the backend and library checks still pass unchanged (`git status` shows no changes under `python/`)
