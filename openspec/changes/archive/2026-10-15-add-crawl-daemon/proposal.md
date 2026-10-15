# Proposal

## Why

There are two ways to run a crawl today. The `crawl` command runs one crawl in the foreground, and its results are gone once they have been printed. The HTTP backend runs many crawls, but it needs a web server, and it loses every job and result when it restarts. A local daemon gives command-line users a third option. They submit crawl jobs from a shell and get their prompt back immediately. Jobs queue up and run in the background, and their results are kept in a database (SQLite by default, PostgreSQL optionally), so they can be queried after the jobs finish and after the daemon restarts.

## What Changes

- Add a new uv project, `python/daemon/` (distribution `crawl-daemon`), that depends on the `site-crawler` library by path, as the backend does. It does not depend on the backend.
- Add a `crawld` command with two groups of subcommands:
  - Lifecycle: `serve` runs the daemon in the foreground. `start` launches it in the background and returns once it is accepting jobs. `stop` shuts it down cleanly. `ping` reports whether it is running.
  - Jobs: `submit` (optionally `--wait`), `list`, `status`, `pages`, `links` and `cancel`. Each has human-readable output by default and `--json` for scripts.
- The daemon listens only on the loopback interface and speaks newline-delimited JSON over TCP. Clients must present a per-daemon token, which the daemon writes to a state file in its data directory along with its port and process id. The CLI finds the daemon through that file.
- Jobs go into a FIFO queue and run with at most N at a time (configurable). A job is `queued`, `running`, `completed`, `failed` or `cancelled`. Queued and running jobs can both be cancelled.
- Add database storage for crawl jobs and their results, behind one storage interface with two implementations:
  - SQLite, the default. It is a file in the data directory and needs no extra dependency.
  - PostgreSQL, chosen with a `postgresql://` database URL. Its driver is an optional extra (`crawl-daemon[postgres]`).
- Implement all three `site-crawler` component interfaces in the daemon, and give every crawl all three explicitly. No crawl relies on the library's fallback components.
  - **Fetcher:** one shared HTTP connection pool for all jobs, like the backend's `SharedClientFetcher`. After each HTML fetch, it also looks the page up in the parse cache.
  - **Parser:** wraps the library's HTML parser with a database-backed parse cache. The cache is keyed by the page's content and final URL, so a page whose content has not changed is not parsed again in any later job, including after a restart. If the cache fails, the parser just parses the page. The cache can be turned off with `CRAWLD_PARSE_CACHE`.
  - **Writer:** stores each page, and the distinct links found on it, in the database while the crawl runs.
- Jobs and results survive a restart. On the next start, queued jobs run. Jobs that were running when the daemon died are marked `failed`, with an error saying the daemon stopped.
- Add a server-side page budget and concurrency limits with the same meaning as the backend's, configured with `CRAWLD_*` environment variables or `serve` options.
- Add a CI job for the daemon (lint, format, type-check, tests), with a PostgreSQL service container so the PostgreSQL storage is tested for real.
- The `site-crawler` library, the `crawl` command, the backend, the dashboard and the Docker stack do not change.

## Capabilities

### New Capabilities

- `crawl-daemon`: a long-running local process that accepts crawl jobs over an authenticated loopback connection, queues them, runs a bounded number at once, and reports their state, results and cancellation. It also covers starting, stopping and recovering after a restart.
- `crawl-daemon-cli`: the `crawld` command used to manage the daemon and submit, inspect and cancel jobs. It covers output formats and exit codes.
- `crawl-result-storage`: keeping crawl jobs, their pages and their distinct links in a SQLite or PostgreSQL database, written as a crawl runs and readable at any time. It also covers the parse cache, which is shared across jobs and kept in the same database.

### Modified Capabilities

None. The daemon provides its own fetcher, parser and writer through `crawler-extension-api` as it is specified, and every job follows `site-crawl` unchanged.

## Impact

- **New code**: `python/daemon/`, with its own `pyproject.toml`, `uv.lock`, `src/crawl_daemon/`, `tests/` and `README.md`.
- **Dependencies (daemon only)**: `site-crawler` (path) and `httpx`. SQLite uses the standard library. `psycopg[binary,pool]` is added only under the `postgres` extra. The library and the backend gain no dependencies.
- **CI**: `.github/workflows/ci.yml` gains a `daemon` job with a `postgres` service.
- **Docs**: a daemon README, plus a pointer from `python/README.md`.
- **Packaging**: `python/pyproject.toml` excludes `/daemon` from the sdist, and ruff excludes it, as it already does for `/backend`.
- **Operational**: the daemon is meant for one local user. It binds to `127.0.0.1` only and requires its token, but it is not hardened for exposure to a network. The SQLite file and the state file are created in a per-user data directory.
