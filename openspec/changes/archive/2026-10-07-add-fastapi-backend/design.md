# Design

## Context

See proposal.md for motivation and specs/crawl-api/spec.md for the required behaviour.

Facts about the library that shape the approach:

- `Crawler(config, fetcher=, parser=, writer=)` accepts any objects matching the `Fetcher`, `Parser` and `Writer` protocols. `run()` returns `CrawlStats`, and `crawler.stats` is a public, live object updated as the crawl progresses.
- `Crawler.run()` always calls `aclose()` on the fetcher and writer in a `finally`, including when the crawl task is cancelled.
- `DefaultHttpxFetcher` accepts an injected `client=httpx.AsyncClient`, but its `aclose()` closes that client regardless of who created it. Its timeout and User-Agent come from the client, not from per-request arguments.
- A failed base URL does not raise: `run()` returns with `stats.seed_ok == False`. `FetchError` on other pages is counted. Any other exception propagates after cleanup.
- `CrawlConfig` validates the URL and limits and raises `ConfigError` (a `ValueError`).

## Goals / Non-Goals

**Goals:**
- One long-running process that runs many crawls concurrently over a single shared HTTP connection pool.
- No change to the `site-crawler` library. The backend uses only its public API and extension points.
- Every endpoint tested without network access, through the real ASGI app.

**Non-Goals:**
- Authentication, rate limiting per client, or protection against crawling internal network addresses (SSRF). The service is for local or trusted use, and the README says so.
- Persistence across restarts, and evicting old jobs from memory.
- Streaming results (SSE or WebSocket), and distributing crawls across processes or machines.
- Per-crawl timeout or User-Agent. These are service-wide settings because the HTTP client is shared.

## Decisions

### 1. Sibling uv project with a path dependency

```
engineer-hiring-tech-exercise/
  python/                       site-crawler (unchanged)
  backend/
    pyproject.toml              name = "crawler-api"
                                [tool.uv.sources] site-crawler = { path = "../python", editable = true }
    uv.lock
    src/crawler_api/
      __init__.py
      main.py                   create_app(settings, fetcher_factory=None), module-level `app`, lifespan
      settings.py               Settings dataclass, from_env()
      schemas.py                pydantic request/response models
      jobs.py                   CrawlJob, JobStatus, JobStore protocol, InMemoryJobStore
      service.py                CrawlService: start / get / list / cancel / shutdown
      adapters.py               SharedClientFetcher, JobWriter
      routes.py                 APIRouter with the endpoints
    tests/
```

The library and the app stay separately versioned and installable, and the library gains no web dependencies. A uv workspace was the alternative; it was rejected so the library's existing layout, lockfile and CI job stay exactly as they are.

The app is run with `uv run uvicorn crawler_api.main:app`. `create_app()` is a factory so tests can pass their own settings and fetcher factory.

### 2. One shared HTTP client, owned by the app lifespan

The FastAPI lifespan creates one `httpx.AsyncClient` and closes it on shutdown, after cancelling running crawls. The client is configured with `follow_redirects=True`, the service User-Agent, `limits.max_connections = settings.max_connections` (a global cap across all crawls), and `httpx.Timeout(settings.request_timeout, pool=None)`.

`pool=None` means a request waits for a free connection instead of failing with `PoolTimeout`. Without it, busy periods would turn into fetch errors, because the fetcher treats `PoolTimeout` as a transport failure.

Each crawl gets a `SharedClientFetcher`, built by composition:

```python
class SharedClientFetcher:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._inner = DefaultHttpxFetcher(client=client)   # reuse retries, body cap, etc.
    async def fetch(self, url: str) -> FetchResult:
        return await self._inner.fetch(url)
    async def aclose(self) -> None:
        pass                                               # the app owns the client
```

Alternatives considered:
- *Change the library so `Crawler` or `DefaultHttpxFetcher` does not close injected resources.* This changes library behaviour and a spec for a backend concern, and existing consumers rely on the close.
- *Subclass `DefaultHttpxFetcher` and override `aclose`.* It works, but composition keeps the backend on the protocol, as the extension spec intends, and doesn't depend on the class staying subclassable.
- *A new client per crawl.* This gives no global connection cap and no connection reuse, and costs a TLS handshake per crawl.

Per-crawl concurrency is still `CrawlConfig.concurrency`, the crawler's worker count. The shared pool caps the total across crawls.

### 3. Jobs, store and service

```
POST /crawls --> CrawlService.start(req)
                   |  validate limits vs Settings; build CrawlConfig (ConfigError -> 422)
                   |  job = CrawlJob(id=uuid4().hex, config, status=RUNNING, started_at)
                   |  crawler = Crawler(config,
                   |      fetcher=fetcher_factory(),             # SharedClientFetcher by default
                   |      parser=DefaultSelectolaxParser(),      # explicit, not the fallback
                   |      writer=JobWriter(job))
                   |  job.stats = crawler.stats                  # live object
                   |  job.task = asyncio.create_task(_run(job, crawler))
                   v
                 store.add(job) --> 202 {id, status, ...}, Location: /crawls/{id}

_run(job, crawler):
    try:     stats = await crawler.run()
             job.status = COMPLETED if stats.seed_ok else FAILED
             (FAILED sets error = "could not fetch base URL <url>")
    except CancelledError:   job.status = CANCELLED      (not re-raised; we cancelled it)
    except Exception as e:   job.status = FAILED; job.error = f"{type(e).__name__}: {e}"; log it
    finally: job.finished_at = now()
```

- `JobStatus` is a `StrEnum`: `running`, `completed`, `failed`, `cancelled`. There is no `queued` state, because crawls start immediately.
- `JobWriter.write()` appends each `PageResult` to `job.pages`, a list. It also adds each of the page's links that hasn't been seen before to the crawl's link index: `job.links`, a list in first-seen order, plus `job.link_set`, a set for O(1) membership checks.
  - Building the index as pages arrive means `GET /crawls/{id}/links` can slice it directly and report `len(job.links)` as the total, without rescanning every page on each request.
  - The page's links are already normalised and de-duplicated within the page by the crawler, so the index only de-duplicates across pages.
  - Pages are delivered one at a time by the crawler's single writer task, so no lock is needed. Reads happen on the same event loop.
- `JobStore` is a protocol (`add`, `get`, `list_recent_first`) with `InMemoryJobStore` backed by an insertion-ordered dict. Newest first is the reversed insertion order. A persistent store would implement the same protocol.
- `CrawlService.cancel(id)` returns 404 if the id is unknown and 409 if the job isn't `running`. Otherwise it calls `task.cancel()` and awaits the task, so the response already shows `cancelled` with the pages kept. The crawler's `finally` closes its writer and fetcher; the fetcher's close is a no-op.
- `CrawlService` keeps a strong reference to each task (on the job), so running tasks aren't garbage-collected.
- `CrawlService.shutdown()`, called from the lifespan, cancels every running task and awaits them before the shared client is closed.

Alternative: FastAPI `BackgroundTasks`. Rejected, because those tasks are tied to the request's lifecycle and can't be cancelled or tracked.

### 4. Validation and limits

`Settings`, read from environment variables with the `CRAWLER_API_` prefix, all optional:

| Setting | Default |
|---|---|
| `default_max_pages` | 1000 |
| `max_pages_limit` | 10000 |
| `default_concurrency` | 8 |
| `max_concurrency` | 32 |
| `max_connections` | 100 |
| `request_timeout` | 10.0 |
| `user_agent` | library default |

It's a plain dataclass with a `from_env()` classmethod. `pydantic-settings` would be an extra dependency for seven values.

The request model `CrawlRequest`:

| Field | Type | Constraints |
|---|---|---|
| `url` | `str` | |
| `max_pages` | `int \| None` | `ge=1` |
| `max_depth` | `int \| None` | `ge=0` |
| `concurrency` | `int \| None` | `ge=1` |
| `respect_robots` | `bool` | default `True` |

Pydantic handles static bounds (422 automatically). The service checks the settings-dependent maxima, and URL validity is left to `CrawlConfig`. Both raise errors that a single exception handler turns into a 422 with the same `{"detail": [...]}` shape FastAPI uses.

Leaving URL checks to `CrawlConfig` keeps one definition of a valid base URL, shared with the CLI. Pydantic's `AnyHttpUrl` was rejected because it normalises the URL (for example, adding a trailing slash) before the crawler sees it.

### 5. API responses

The endpoints and their responses:

| Endpoint | Response |
|---|---|
| `POST /crawls` | 202 with a `CrawlSummary` and a `Location` header |
| `GET /crawls` | `list[CrawlSummary]` |
| `GET /crawls/{id}` | `CrawlDetail`; 404 if the id is unknown |
| `GET /crawls/{id}/status` | `CrawlStatus`; 404 if the id is unknown |
| `GET /crawls/{id}/pages?offset=0&limit=100` | `PageList` (`limit` must be 1-1000, `offset` must be ≥0); 404 if the id is unknown |
| `GET /crawls/{id}/links?offset=0&limit=100` | `LinkList` (same `offset`/`limit` rules); 404 if the id is unknown |
| `DELETE /crawls/{id}` | 200 with a `CrawlDetail`; 404 if unknown, 409 if not running |
| `GET /health` | `{"status": "ok"}` |

The response models:

- **`CrawlSummary`**: `id`, `url`, `status`, `started_at`, `finished_at`, `stats` (`pages`, `fetched`, `errors`, `robots_skipped`).
- **`CrawlDetail`**: everything in `CrawlSummary`, plus `limits` (the effective `max_pages`, `max_depth`, `concurrency`, `respect_robots`) and `error`.
- **`CrawlStatus`**: `id`, `status`, `started_at`, `finished_at`, `stats` and `error`. It has no URL, limits or results, so clients can poll it cheaply. `CrawlDetail` is the full view; the status endpoint is the one to poll.
- **`PageList`**: `total`, `offset`, `limit`, and `items: [{url, links}]`.
- **`LinkList`**: `total`, `offset`, `limit`, and `items: [str]`, the distinct links in first-seen order. It includes links the crawl didn't follow (other hosts, robots.txt, beyond limits), because it lists what was found, not what was fetched.

The crawl list (`GET /crawls`) isn't paginated. Jobs are in memory and few, and the non-goals already exclude unbounded retention.

### 6. Testing approach

- Tests drive the real app with `httpx.AsyncClient(transport=httpx.ASGITransport(app))` inside `app.router.lifespan_context(app)`, so startup and shutdown run. No extra lifespan dependency is needed.
- `create_app(fetcher_factory=...)` injects in-memory fakes, written in `backend/tests/fakes.py` because the library's test fakes aren't installed with the package:
  - `FakeSite`, which serves canned pages.
  - `GatedSite`, which blocks fetches until an `asyncio.Event` is set. It makes "still running" and "cancel mid-crawl" states deterministic, without sleeps.
- Tests wait for a crawl to finish by polling `GET /crawls/{id}/status` with a short `asyncio.sleep(0)` loop and an overall timeout.
- One test uses the default `SharedClientFetcher` with `respx` mocking HTTP. It checks the real adapter end to end, and that the shared client is still usable after a crawl completes.
- Test tooling matches the library's: pytest, pytest-asyncio (auto mode), respx, ruff, and mypy in strict mode.

### 7. CI

A second job, `backend`, in `.github/workflows/ci.yml`, with `working-directory: backend`. It runs the same steps: `uv sync --locked`, ruff check, ruff format check, mypy and pytest, on Python 3.12 and 3.13. Checkout already includes `python/`, so the path dependency resolves.

## Risks / Trade-offs

- [Jobs, pages and link indexes accumulate in memory with no eviction] → The default and maximum page budgets bound each crawl. The link index stores references to the same link strings as the pages, so it costs a list and a set per crawl, not a second copy of the URLs. The README documents the limitation, and the `JobStore` protocol is the seam for a bounded or persistent store.
- [No auth, and crawls can target any host, including internal addresses] → Documented as local or trusted use only. Production would need auth and an allow or deny list for target hosts.
- [Many crawls compete for the shared pool, so individual crawls slow down] → This is intended, as the global cap protects the host. `pool=None` means contention adds delay but not errors. `max_connections` is configurable.
- [A cancelled crawl's in-flight fetches are abandoned mid-request] → `Crawler.run()` cancels its workers and closes the writer, httpx releases the connections on cancellation, and the pages already reported are kept.
- [The `stats` object is mutated by the crawler while it's read by request handlers] → Both run on one event loop with no `await` between reads, so responses see a consistent snapshot.
- [The service-wide timeout and User-Agent are less flexible than the CLI's options] → Accepted (see Non-Goals). They could be made per-crawl later with per-request httpx options.
- [The path dependency means the backend can't be installed on its own from an index] → Acceptable for a monorepo. Publishing `site-crawler` would replace the path source with a version pin.
