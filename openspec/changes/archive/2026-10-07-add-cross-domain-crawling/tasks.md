# Tasks

Paths are relative to `engineer-hiring-tech-exercise/`. Python commands run from the named uv project; npm commands from `front-end/`.

## 1. Scope model (library)

- [x] 1.1 In `python/src/site_crawler/core/urls.py`, add `HostPattern`, `parse_host_pattern` (exact host with optional port, IPv4/bracketed IPv6, leading `*.` wildcard; lowercase, strip trailing dot; reject scheme, path, `@`, whitespace, empty, bare `*` and inner `*` with a `ConfigError` naming the pattern) and `HostScope(base_host, patterns).allows(url)`; add tests in `python/tests/test_urls.py` for each valid and invalid case and for matching (exact, wildcard depth, apex not matched by a wildcard, case, ports); verify `uv run pytest tests/test_urls.py` passes in `python/`
- [x] 1.2 Add `allowed_hosts: tuple[str, ...] = ()` (validated and stored normalised) and `per_host_concurrency: int | None = None` (at least 1) to `CrawlConfig`; add tests for normalisation, invalid patterns and `per_host_concurrency=0`; verify `uv run pytest` and `uv run mypy` pass in `python/`

## 2. Crawler (library)

- [x] 2.1 Make `RobotsGate.load` take an origin (`scheme://host/`), and change the crawler's queue to `Fetch` and `LoadRobots` items with per-host `pending` lists and the synchronous `_admit` described in design.md decision 2. Replace both `same_host` checks with `HostScope.allows`. Verify the whole existing suite (`uv run pytest` in `python/`) passes unchanged
- [x] 2.2 Add multi-host crawler tests (extend `tests/fakes.py` so `FakeSite` can serve several hosts and per-host `robots.txt`): allowed exact host followed and its links followed; wildcard matches subdomains but not other domains; an out-of-scope link is only reported; a redirect to an allowed host is reported under the final URL; robots.txt is fetched once per host and applied per host; robots-disallowed URLs on an allowed host don't use up the page budget; verify `uv run pytest` passes
- [x] 2.3 Add the per-host semaphore around fetches (including `LoadRobots`) when `per_host_concurrency` is set; add a test with a fetcher that records the maximum number of in-flight requests per host (two busy hosts, concurrency 8, cap 2, so at most 2 per host) and a test that no cap leaves single-host concurrency unchanged; verify `uv run pytest`, `uv run mypy` and `uv run ruff check` pass in `python/`

## 3. CLI and library docs

- [x] 3.1 Add `--allow-host PATTERN` (repeatable) and `--per-host-concurrency N` to `cli.py`, passed into `CrawlConfig`; add `tests/test_cli.py` cases (options reach the config, an invalid pattern exits 2 with the message); update `python/README.md` (CLI options, the scope and robots.txt-per-host notes in the design section, the head-of-line blocking note in "Future work"); verify `uv run pytest tests/test_cli.py` passes and `uv run crawl --help` lists both options

## 4. Backend

- [x] 4.1 Add `allowed_hosts` (list, `max_length=50`) and `per_host_concurrency` (`ge=1`) to `CrawlRequest`, `allowed_hosts` and `per_host_concurrency` to `Limits`, and pass them through `CrawlService.start` (with `LimitError` when `per_host_concurrency` exceeds `max_concurrency`); add service and API tests for the spec scenarios (cross-domain start, details with empty and non-empty `allowed_hosts`, an allowed host's page in the results, an invalid pattern, 51 patterns, per-host concurrency above the maximum); update `python/backend/README.md` (request fields); verify `uv run ruff check`, `uv run mypy` and `uv run pytest` pass in `python/backend/`

## 5. Dashboard

- [x] 5.1 Run `npm run gen:api` and commit the regenerated `src/lib/api`; verify `npm run typecheck` passes and the diff only adds the new fields
- [x] 5.2 Add the "Also follow hosts" textarea and the "Per-host concurrency" field to `StartCrawlForm` (split on commas and whitespace, drop blanks, send only when not empty; map a 422 at `loc[1] = "allowed_hosts"` to the textarea) and show the allowed hosts (or "base host only") and per-host concurrency in `CrawlView`'s limits; extend `src/test/fakeApi.ts` and add tests for the also-follow-hosts scenario, the field error, and the allowed-hosts display; verify `npm run lint`, `npm run typecheck`, `npm test -- --run` and `npm run build` pass

## 6. Integration check

- [x] 6.1 With `docker compose up --build`, start a crawl from the dashboard of `https://toscrape.com/` with "also follow hosts" set to `*.toscrape.com` and a page budget of 30, and confirm that pages from `books.toscrape.com` or `quotes.toscrape.com` appear, the crawl view lists the allowed host, and the same crawl without the pattern reports those subdomain links without fetching them; run `bash scripts/docker-smoke.sh`; verify all CI checks pass locally for the library, backend and front-end (including the API contract drift check)
