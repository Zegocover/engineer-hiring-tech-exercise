# crawler-api

An HTTP service for running [`site-crawler`](../README.md) crawls. You start a crawl with one request and it
runs in the background. You can then poll its status, page through the pages and links it finds, or cancel it, and
several crawls can run at once in one process.

Each crawl follows the same rules as the `crawl` command:

- It stays on the base URL's host.
- It fetches each normalised URL once.
- It respects robots.txt unless the request turns that off.

A web dashboard for this API (Next.js) lives in [`front-end/`](../../front-end/README.md#solution-crawler-dashboard).
It calls the API from its own server, so the API needs no CORS setup.

## Running it

To run it together with the dashboard in Docker, see [Run everything with Docker](../../README.md#run-everything-with-docker).

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/). The `site-crawler` library is installed from the parent
`python/` folder (`..`) as an editable path dependency.

```bash
cd python/backend
uv sync
uv run uvicorn crawler_api.main:app            # http://127.0.0.1:8000, docs at /docs
```

### Development

```bash
uv run pytest           # tests (no network: in-memory fetchers and respx)
uv run mypy             # strict type checking
uv run ruff check       # lint
uv run ruff format      # format
```

## API

| Method and path | Purpose |
|---|---|
| `POST /crawls` | Start a crawl. Returns 202 with its `id` and a `Location` header. |
| `GET /crawls` | List all crawls, newest first. |
| `GET /crawls/{id}` | Full details, including the limits actually applied. |
| `GET /crawls/{id}/status` | Lightweight status and statistics. Use this endpoint for polling. |
| `GET /crawls/{id}/pages?offset=0&limit=100` | The pages found so far, each with its links, in the order they were reported. |
| `GET /crawls/{id}/links?offset=0&limit=100` | Every distinct link found so far, in first-seen order. This includes links that weren't followed. |
| `DELETE /crawls/{id}` | Cancel a running crawl. The pages found so far are kept. Returns 409 if the crawl has already finished. |
| `GET /health` | Liveness check. |

A crawl's `status` is `running`, `completed`, `failed` or `cancelled`. A crawl is `failed` when its base URL can't
be fetched or it hits an unexpected error, and `error` says why. If other pages fail, they're counted in
`stats.errors` and the crawl still completes.

Invalid requests get a 422 and no crawl is created. That covers a URL that isn't an absolute `http(s)` URL, a
negative depth, or a page budget or concurrency above the service maximum.

### Example

```bash
$ curl -si -X POST localhost:8000/crawls -H 'content-type: application/json' \
       -d '{"url": "https://books.toscrape.com/", "max_pages": 50, "concurrency": 8}'
HTTP/1.1 202 Accepted
location: /crawls/5f0c...
{"id":"5f0c...","url":"https://books.toscrape.com/","status":"running", ...}

$ curl -s localhost:8000/crawls/5f0c.../status
{"id":"5f0c...","status":"completed","started_at":"...","finished_at":"...",
 "stats":{"pages":50,"fetched":50,"errors":0,"robots_skipped":0},"error":null}

$ curl -s 'localhost:8000/crawls/5f0c.../pages?limit=1'
{"total":50,"offset":0,"limit":1,"items":[{"url":"https://books.toscrape.com/","links":["..."]}]}

$ curl -s 'localhost:8000/crawls/5f0c.../links?limit=3'
{"total":...,"offset":0,"limit":3,"items":["https://books.toscrape.com/index.html", "..."]}

$ curl -s -X DELETE localhost:8000/crawls/5f0c...
```

The request body accepts these fields; everything except `url` is optional:

| Field | Meaning |
|---|---|
| `url` | The base URL. Required. |
| `max_pages` | The page budget. Defaults to the service's default. |
| `max_depth` | How many link hops from the base URL to follow. |
| `concurrency` | Parallel requests for this crawl. |
| `respect_robots` | Whether to obey robots.txt. Defaults to `true`. |
| `allowed_hosts` | Extra hosts to follow besides the base URL's, up to 50: `docs.example.org`, `localhost:8001`, or `*.example.com` for any subdomain (not `example.com` itself). Links to other hosts are still only reported. Defaults to none. |
| `per_host_concurrency` | Most parallel requests to any one host, at most the service's maximum concurrency. Defaults to no extra limit. |

## Settings

Set these through environment variables; all are optional.

| Variable | Default | Meaning |
|---|---|---|
| `CRAWLER_API_DEFAULT_MAX_PAGES` | 1000 | Page budget when a request doesn't set `max_pages`. |
| `CRAWLER_API_MAX_PAGES_LIMIT` | 10000 | Largest `max_pages` a request may ask for. |
| `CRAWLER_API_DEFAULT_CONCURRENCY` | 8 | Per-crawl concurrency when a request doesn't set it. |
| `CRAWLER_API_MAX_CONCURRENCY` | 32 | Largest per-crawl concurrency a request may ask for. |
| `CRAWLER_API_MAX_CONNECTIONS` | 100 | HTTP connections shared by all crawls together. |
| `CRAWLER_API_REQUEST_TIMEOUT` | 10.0 | Per-request timeout in seconds. |
| `CRAWLER_API_USER_AGENT` | library default | User-Agent sent with every request. |

## How it is wired

```
src/crawler_api/
  main.py       create_app(): lifespan owns one shared httpx.AsyncClient and the CrawlService
  routes.py     the /crawls endpoints
  service.py    CrawlService: validates limits, starts each crawl as an asyncio task, cancel, shutdown
  adapters.py   SharedClientFetcher and JobWriter, the backend's own crawler components
  jobs.py       CrawlJob, JobStatus, JobStore protocol and InMemoryJobStore
  schemas.py    request and response models
  settings.py   Settings.from_env()
```

The service gives every crawl its components explicitly:

- **Fetcher:** a `SharedClientFetcher`. It reuses the library's `DefaultHttpxFetcher` retry logic over the app's
  single client. Its `aclose()` does nothing, because the crawler closes its fetcher when a crawl ends but the
  client is shared with every other crawl.
- **Parser:** a `StdlibHtmlParser`, built on Python's standard-library `html.parser`. It returns the same links as
  the library's selectolax-based default; `tests/test_parser.py` checks that on 26 tricky HTML cases. The one
  difference is in its favour: it honours the charset in the `Content-Type` header, which selectolax ignores.
- **Writer:** a `JobWriter`, which appends each page to its job and keeps a de-duplicated index of links, so the
  links endpoint is a cheap slice.

The shared client caps connections across all crawls. It waits for a free connection rather than timing out
(`pool=None`), so a busy period slows crawls down instead of turning into fetch errors.

On shutdown, running crawls are cancelled and awaited before the client is closed.

## Limitations

- **Parsing is pure Python, so it's slower than selectolax.** On a 207 KiB page with 1,500 links it takes about
  28 ms against selectolax's 3 ms (typical pages: roughly 3-14 ms). Parsing runs on the event loop, so very large
  pages hold it briefly; network time still dominates crawls. A `<meta charset>` tag isn't read (selectolax doesn't
  read it either here), so such pages are decoded as UTF-8 unless the header names the charset.
- **In memory only.** Jobs and results are lost on restart and never evicted. The page budgets bound each crawl,
  and `JobStore` is the place to plug in a bounded or persistent store.
- **No authentication, and no protection against crawling internal addresses (SSRF).** Run it locally or behind
  something that provides both.
- **Timeout and User-Agent are service-wide.** They're properties of the shared client, not per crawl.
- **No result streaming.** Clients poll `/status` and page through `/pages` and `/links`.
