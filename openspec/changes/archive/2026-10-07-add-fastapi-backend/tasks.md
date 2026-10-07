# Tasks

All paths are relative to `engineer-hiring-tech-exercise/`. Run commands from `backend/` unless stated otherwise.

## 1. Project scaffolding

- [x] 1.1 Create `backend/pyproject.toml` (project `crawler-api`, Python >=3.12, hatchling with `packages = ["src/crawler_api"]`, dependencies `fastapi`, `uvicorn`, `httpx`, `site-crawler`, with `[tool.uv.sources] site-crawler = { path = "../python", editable = true }`, a dev group with pytest, pytest-asyncio, respx, ruff and mypy, and ruff/mypy/pytest settings matching `python/pyproject.toml`), plus `backend/.gitignore` and an empty `src/crawler_api/__init__.py` and `py.typed`; verify `uv sync` succeeds and `uv run python -c "import crawler_api, site_crawler"` works

## 2. Settings, jobs and store

- [x] 2.1 Implement `settings.py`: a `Settings` dataclass with the defaults from design.md and `Settings.from_env()` reading `CRAWLER_API_*` variables; add `tests/test_settings.py` covering the defaults and an environment override; verify `uv run pytest tests/test_settings.py` passes
- [x] 2.2 Implement `jobs.py`: a `JobStatus` StrEnum, a `CrawlJob` dataclass (id, config, status, started_at, finished_at, pages, links, link_set, stats, error, task), a `JobStore` protocol and `InMemoryJobStore` (`add`, `get`, `list_recent_first`); add `tests/test_jobs.py` covering get-unknown and newest-first ordering; verify `uv run pytest tests/test_jobs.py` passes

## 3. Backend adapters

- [x] 3.1 Implement `adapters.py`: `SharedClientFetcher`, which delegates `fetch` to `DefaultHttpxFetcher(client=...)` and does nothing on `aclose`, and `JobWriter`, which appends each `PageResult` to `job.pages` and adds unseen links to `job.links`/`job.link_set` in first-seen order; add `tests/test_adapters.py` with respx checking that a fetch succeeds, that the shared client is not closed after `aclose()`, that `JobWriter` records pages in order, and that a link found on two pages appears once in `job.links` at its first position; verify `uv run pytest tests/test_adapters.py` passes

## 4. Crawl service

- [x] 4.1 Add `tests/fakes.py` with `FakeSite` (canned pages, failing URLs) and `GatedSite` (fetches block until an `asyncio.Event` is set) implementing the `Fetcher` protocol, plus a line-based parser if needed; verify `uv run mypy` passes on the new file
- [x] 4.2 Implement `service.py` `CrawlService.start`: validate the limits against `Settings` (applying the defaults), build the `CrawlConfig`, wire `Crawler` with `fetcher_factory()`, an explicit `DefaultSelectolaxParser()` and `JobWriter`, then store the job and start its task; the `_run` wrapper sets `completed`, `failed` (seed failure or an unexpected exception, with an error message) or `cancelled`; add `tests/test_service.py` covering completed with stats, a seed failure, an unexpected parser exception and the limits rejection; verify `uv run pytest tests/test_service.py` passes
- [x] 4.3 Implement `CrawlService.get`, `list`, `cancel` (unknown, not running → conflict, otherwise cancel and await) and `shutdown` (cancel and await every running task); extend `tests/test_service.py` with cancel mid-crawl via `GatedSite` (pages kept, status `cancelled`), cancel of a finished crawl, two concurrent crawls where cancelling one leaves the other to complete, and shutdown cancelling running crawls; verify `uv run pytest tests/test_service.py` passes

## 5. HTTP API

- [x] 5.1 Implement `schemas.py` (`CrawlRequest`, `CrawlSummary`, `CrawlDetail`, `CrawlStatus`, `PageList`, `LinkList`, stats and limits models) as in design.md; verify `uv run mypy` passes
- [x] 5.2 Implement `main.py` `create_app(settings=None, fetcher_factory=None)` with a lifespan that creates the shared `httpx.AsyncClient` (global connection cap, `pool=None` timeout, service User-Agent), builds the `CrawlService`, calls `shutdown()` and then closes the client; also add a module-level `app`, `GET /health` and the exception handler mapping `ConfigError` and limit errors to a 422; add `tests/conftest.py` with an app/client fixture using `ASGITransport` inside `app.router.lifespan_context`, and `tests/test_api.py::test_health`; verify `uv run pytest tests/test_api.py` passes
- [x] 5.3 Implement `routes.py`: `POST /crawls` (202 + `Location`), `GET /crawls`, `GET /crawls/{id}`, `GET /crawls/{id}/status`, `GET /crawls/{id}/pages` (offset/limit), `GET /crawls/{id}/links` (offset/limit), `DELETE /crawls/{id}` (404/409); extend `tests/test_api.py` with one test per spec scenario in `specs/crawl-api/spec.md` (start, ftp URL rejected and not listed, negative depth, default page budget, page budget above max, details with effective limits and unknown crawl, status running/completed/unknown, paged results and results while running, links de-duplicated across pages, links not followed listed, paged links and links of an unknown crawl, newest-first listing, off-host link not fetched, cancel running/finished/unknown, base URL failure, one page failure); verify `uv run pytest tests/test_api.py` passes
- [x] 5.4 Add `tests/test_end_to_end.py`: start the app with the default `SharedClientFetcher`, mock a small site with respx, run two crawls back to back, and check both complete with the expected pages (proving the shared client survives a crawl); verify `uv run pytest tests/test_end_to_end.py` passes

## 6. Documentation and CI

- [x] 6.1 Write `backend/README.md` covering how to run it (`uv run uvicorn crawler_api.main:app`), the settings, curl examples for each endpoint, and the limitations (in-memory, no auth or SSRF protection, service-wide timeout and User-Agent); add a short "HTTP backend" pointer in `python/README.md`'s design discussion; verify that running the server locally and following the README's curl example for `POST /crawls`, `GET /crawls/{id}/status` and `GET /crawls/{id}/links` behaves as documented
- [x] 6.2 Add a `backend` job to `.github/workflows/ci.yml` (`working-directory: backend`; Python 3.12 and 3.13; `uv sync --locked`, ruff check, ruff format check, mypy, pytest); verify the workflow YAML parses and that the same commands pass locally from `backend/`

## 7. Integration check

- [x] 7.1 From `backend/`, run `uv run ruff check`, `uv run ruff format --check`, `uv run mypy` and `uv run pytest`; from `python/`, run `uv run pytest` to confirm the library is untouched; verify everything passes and `git status` shows no changes under `python/src`
