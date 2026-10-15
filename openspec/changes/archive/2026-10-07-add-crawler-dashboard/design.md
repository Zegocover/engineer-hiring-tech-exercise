# Design

## Context

See proposal.md for motivation and specs/crawl-dashboard/spec.md for behaviour. Paths are relative to `engineer-hiring-tech-exercise/`.

- **The crawl API** (`python/backend`, port 8000 by default) has seven operations the dashboard uses. Its OpenAPI schema (`create_app().openapi()`) defines every request and response model.
- **The schema only documents 422 errors.** 404 and 409 come from `HTTPException`, and the two use different error bodies (verified against the running app):
  - 404 and 409: `{"detail": "crawl nope not found"}`, where `detail` is a string.
  - 422: `{"detail": [{"loc": ["body", "max_depth"], "msg": "...", "type": "..."}]}`. When the error isn't tied to a field, `loc` is just `["body"]`.
- **`front-end/` contains only `README.md`**, the brief for the separate front-end exercise, which is kept.
- **Tooling:** Node 24 and npm 11 are installed locally. Current major versions are Next 16, React 19 and TanStack Query 5.

## Goals / Non-Goals

**Goals:**
- A small, well-tested Next.js app that exercises every crawl API endpoint through its own server.
- Types that can't drift from the backend: generated from its schema, and checked in CI.
- Tests that need neither a network nor a running backend.

**Non-Goals:**
- Solving the front-end exercise (server-driven form UI). The README says so explicitly.
- Authentication, multi-user features, or charts and graphs of the link structure.
- Browser end-to-end tests (Playwright). The README discusses how they'd be added. The final task checks the integration manually against both real servers.
- Any change to the crawl API.

## Decisions

### 1. Layout

```
front-end/
  README.md                      existing brief + new "Solution" section
  package.json, package-lock.json, next.config.ts, tsconfig.json, eslint.config.mjs
  vitest.config.mts, vitest.setup.ts
  scripts/gen-api.mjs            regenerates the API contract from the backend
  src/
    app/
      layout.tsx                 html shell + <Providers> (QueryClient)
      page.tsx                   "/" : StartCrawlForm + CrawlList
      crawls/[id]/page.tsx       "/crawls/:id" : CrawlView
      api/crawls/route.ts                    GET (list), POST (start)
      api/crawls/[id]/route.ts               GET (detail), DELETE (cancel)
      api/crawls/[id]/status/route.ts        GET
      api/crawls/[id]/pages/route.ts         GET (?offset&limit)
      api/crawls/[id]/links/route.ts         GET (?offset&limit)
    lib/
      api/openapi.json           generated: backend schema snapshot
      api/schema.d.ts            generated: openapi-typescript output
      api/types.ts               friendly aliases (CrawlDetail, CrawlStatus, ...)
      backend.ts                 server-only: forward(request, path) to the crawl API
      client.ts                  browser: typed fetch wrappers + ApiError
      polling.ts                 poll intervals (overridable in tests)
    components/
      StartCrawlForm.tsx, CrawlList.tsx, CrawlView.tsx, StatusBadge.tsx,
      Paginator.tsx, PagesTab.tsx, LinksTab.tsx, ApiErrorNotice.tsx
    test/                        MSW handlers, fixtures and render helpers
```

**Scaffolding:** `create-next-app` refuses a non-empty directory. So the app is generated in a temporary directory with TypeScript, ESLint, Tailwind, App Router, `src/` and npm, then moved into `front-end/`. Its README is dropped so the existing one stays. The versions it pins are kept as they are.

### 2. One explicit route handler per operation, sharing a single forwarder

```
browser --fetch /api/crawls/42/pages?offset=50--> route.ts (GET)
                                                     |
                                     forward(req, `/crawls/${id}/pages`)
                                                     |
             fetch(`${CRAWLER_API_URL}/crawls/42/pages?offset=50`, {signal: timeout(10s)})
                                                     |
              <-- same status + JSON body ------------+    or 502 {"detail": "Crawler API is unreachable"}
```

`forward()` lives in `lib/backend.ts`, which imports `server-only`. It:
- copies the method, query string and JSON body;
- returns the backend's status and body unchanged;
- maps network errors and timeouts (`AbortSignal.timeout`) to a 502;
- reads `process.env.CRAWLER_API_URL`, defaulting to `http://localhost:8000`, at request time.

That variable has no `NEXT_PUBLIC_` prefix, so Next.js never includes it in the browser bundle. Path ids are `encodeURIComponent`-escaped before they're interpolated.

Alternatives considered:
- *A catch-all `api/[...path]` proxy.* It's less code, but it forwards anything, including paths the dashboard never uses. Explicit handlers are the allow-list the spec requires, and an unmatched path gets Next.js's 404 automatically.
- *`rewrites` in `next.config`.* This was rejected in exploration in favour of route handlers: rewrites can't turn an unreachable backend into a clear 502, and they forward every path.

Next 16 detail: route handler `params` is a `Promise` and must be awaited.

### 3. Generated, committed API types with a drift check

`npm run gen:api` runs `scripts/gen-api.mjs`, which:
1. spawns `uv run --project ../python/backend python -c "<dump create_app().openapi() as JSON>"`. It's spawned with an argument array, with no shell, so quoting works on Windows and Linux.
2. writes `src/lib/api/openapi.json`.
3. runs `openapi-typescript` programmatically to produce `src/lib/api/schema.d.ts`.

Both outputs are committed, so building the dashboard doesn't need Python. CI regenerates them and runs `git diff --exit-code src/lib/api`, so a backend change that alters the API fails the front-end job until the types are regenerated.

`openapi-fetch` was considered for typed calls, but it targets the backend's paths. The browser calls the dashboard's `/api/...` paths, which mirror them, so a small hand-written `client.ts` using the generated *model* types is clearer than adapting a path-typed client.

### 4. Client data: TanStack Query, polling only when something is running

| Query | Key | Refetch interval |
|---|---|---|
| Crawl list | `["crawls"]` | `LIST_MS` (2 s) while any crawl is `running`, or while the last fetch failed (so the list recovers when the backend comes back); otherwise off |
| Detail (URL, limits) | `["crawl", id]` | none (static) |
| Status | `["crawl", id, "status"]` | `STATUS_MS` (1 s) while `running`, then `false` |
| Pages / links | `["crawl", id, "pages" \| "links", offset]` | `RESULTS_MS` (2 s) while the status is `running`; `placeholderData: keepPreviousData` |

The intervals come from `lib/polling.ts`, so tests can shorten them.

- **Starting a crawl** is a mutation. On success it invalidates `["crawls"]` and navigates with `router.push(`/crawls/${id}`)`.
- **Cancelling** is a mutation. A 200 writes the returned detail into the cache. A 409 refetches the status, which covers the race in the spec. Both invalidate the list.
- **Retries:** queries don't retry 4xx responses (a 404 is final). They retry other failures once, so a 502 shows quickly.

SWR was considered as an alternative. TanStack Query's per-query `refetchInterval` callback and mutation handling fit these polling rules more directly.

### 5. Errors in the UI

`client.ts` throws `ApiError { status, detail }` for any response that isn't 2xx, where `detail` is either a string or a list of validation errors.

- **`ApiErrorNotice`** shows:
  - a 502 as "The crawler API is unreachable (is it running on …?)";
  - a 404 as "Crawl not found", with a link back;
  - anything else as its string `detail`.
- **`StartCrawlForm`** maps each 422 entry by `loc[1]` to a field (`url`, `max_pages`, `max_depth`, `concurrency`). An entry with only `loc: ["body"]`, or naming an unknown field, goes to a message at the top of the form.

### 6. UI

Plain Tailwind (create-next-app's default) and semantic HTML, with no component library:
- labelled form controls;
- `role="tablist"`/`tab`/`tabpanel` for the pages and links tabs;
- `aria-live="polite"` on the status and statistics, so screen readers hear progress;
- a page size of 50 for pages and links, with a "51-100 of 120" range label.

### 7. Testing

- **Vitest, React Testing Library and jsdom** for components. **MSW** intercepts `fetch` to `/api/...` using fixtures typed with the generated models.
  - `client.ts` builds URLs against `window.location.origin` in the browser, because relative `fetch` URLs don't resolve under Node's fetch in jsdom.
- **Route handler tests** run in the `node` environment. They call the exported `GET`, `POST` and `DELETE` functions with real `Request` objects, and MSW plays the crawl API at `CRAWLER_API_URL`. That covers pass-through of each status, forwarding of query and body, and the 502 on connection refusal and on timeout.
- **Polling tests** shorten the intervals and use MSW handlers whose responses move from `running` to `completed`. They assert that no further status requests are made afterwards.

### 8. CI

A `front-end` job with `working-directory: front-end` on Node 24. It runs:
- `npm ci`
- `npm run lint`
- `npx tsc --noEmit`
- `npm test -- --run`
- `npm run build`
- a contract drift step: `setup-uv`, then `npm run gen:api` and `git diff --exit-code src/lib/api`.

## Risks / Trade-offs

- [Two places to run for local development: the backend and the dashboard] → The README gives both commands side by side. Running them together, for example with Docker Compose, is listed as future work.
- [Error response shapes aren't in the backend's OpenAPI schema] → `ApiError.detail` is typed as `string | ValidationError[]`, and both shapes are covered by tests. Adding `responses=` to the backend routes would document them, but that's a crawl API change, out of scope here.
- [Polling costs requests] → Only crawls that are running are polled, at 1-2 s, and polling stops when nothing is running. Streaming results is already a backend non-goal.
- [Fast-moving majors (Next 16, React 19, TypeScript 7) can break test tooling] → Keep the versions create-next-app pins, and lock them with `package-lock.json`. If a test tool doesn't yet support a major, pin the previous major of that tool and record why in the README.
- [The proxy adds latency] → It's one hop on localhost, which is negligible against crawl times, and in exchange there's no CORS and the backend stays private.
- [The README for a different exercise lives in the same folder] → The Solution section opens by stating this app's purpose, and the original brief stays above it untouched.
