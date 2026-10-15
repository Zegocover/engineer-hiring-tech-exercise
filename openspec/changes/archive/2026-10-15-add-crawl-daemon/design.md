# Design

## Context

See proposal.md for the motivation. These facts about the current code shape the approach:

- **The library takes pluggable components.** `site_crawler.Crawler(config, fetcher=, parser=, writer=)` accepts any objects that match the `Fetcher`, `Parser` and `Writer` protocols. `Writer` is just `async write(PageResult)` and `async aclose()`. The crawler sends results to the writer one at a time, from a single task, in a stable order. `crawler.stats` is a live `CrawlStats` object. `Fetcher.fetch` and the `Writer` methods are async, but `Parser.parse(FetchResult) -> list[str]` is **synchronous** and is called on the event loop (`core/crawler.py:233`). A parser therefore cannot await a database query.
- **The backend already has the job pattern, but it is tied to the backend.** `python/backend/src/crawler_api/` has `CrawlService`, `CrawlJob`, `JobStore` (a protocol with an in-memory implementation) and `SharedClientFetcher`. Its job model keeps pages in process memory, has no `queued` state, and lives in a package that depends on FastAPI. The user asked for a standalone daemon project.
- **This is a monorepo of separate uv projects.** `python/` is the library, and `python/backend/` is a separate uv project that depends on the library by path, has its own lint, type-check and test config, and has its own CI job. The daemon follows the same layout.
- **The user's machine runs Windows,** and CI runs Linux. The daemon has to work on both. That excludes `fork()`-based daemonisation and makes Unix-socket-only IPC awkward, because asyncio's Windows Proactor loop has no Unix sockets.

## Goals / Non-Goals

**Goals:**
- A self-contained daemon package that can be tested without a network: fake fetchers, ephemeral ports, temporary data directories.
- One storage abstraction that serves both as the job store and as the crawl writer, with SQLite and PostgreSQL implementations that pass the same contract test suite.
- Fully cross-platform: `start` and `stop` work on Windows, macOS and Linux with no service manager.

**Non-Goals:**
- Resuming an interrupted crawl from where it stopped. The crawl frontier is not persisted, so an interrupted job is marked failed rather than resumed.
- Running as an OS service (systemd unit, Windows service, launchd). Users can wrap `crawld serve` themselves.
- Remote or multi-user access, TLS, or more than one daemon sharing one database.
- Changes to the library, the backend, the dashboard or the Docker stack.
- Retention or pruning of old jobs. A later `crawld prune` could add it.

## Decisions

### 1. A new sibling uv project, `python/daemon/`, package `crawl_daemon`

This mirrors `python/backend/`: its own `pyproject.toml` (ruff, strict mypy and pytest settings copied from the backend), `site-crawler` as a path dependency through `[tool.uv.sources]`, and a `crawld = "crawl_daemon.cli:main"` script.

Module layout, where each module imports only the ones listed before it:
- `settings.py` holds the `Settings` dataclass, read from `CRAWLD_*` variables. It follows the backend's `Settings.from_env` pattern and adds `max_parallel_jobs`, `data_dir`, `database_url` and `port`.
- `models.py` holds `JobStatus` (adds `QUEUED`), `JobRecord`, `JobLimits` and the error types.
- `storage/` holds the `Storage` protocol, `sqlite.py`, `postgres.py`, and `open_storage(url)`.
- `components/` holds the daemon's implementations of the library's interfaces: `fetcher.py` (`SharedClientFetcher`), `parser.py` (`CachingParser` and the per-job `ParseCache`) and `writer.py` (`StorageWriter`). See decision 8.
- `protocol.py` holds request and response framing, plus encoding and decoding.
- `scheduler.py` holds `JobScheduler`: the queue, worker slots, cancellation, shutdown and recovery.
- `server.py` holds the asyncio TCP server: authentication, dispatch to the scheduler and storage, and the state file.
- `client.py` holds `DaemonClient`, a small synchronous client used by the CLI.
- `cli.py` holds the argparse subcommands, output formatting and exit codes.

*Alternatives:* importing `CrawlService` from `crawler-api` was rejected, because it drags in FastAPI and couples the two projects, which the user declined. Moving the shared job code into the library was rejected because it would change the library's scope.

### 2. IPC: newline-delimited JSON over loopback TCP

The daemon serves with `asyncio.start_server(host="127.0.0.1", port=...)`. Each request is one JSON line, `{"op": "submit", "token": "...", "args": {...}}`. Each response is one line, `{"ok": true, "result": ...}` or `{"ok": false, "error": {"code": "not_found", "message": "..."}}`. A connection can carry many requests in sequence. Lines are capped at 1 MiB with the `StreamReader` `limit`. Over the limit, the daemon sends an `invalid_request` error and closes the connection.

Operations: `ping`, `submit`, `get`, `list`, `pages`, `links`, `cancel` and `shutdown`. Error codes: `unauthorized`, `invalid_request`, `not_found`, `conflict` and `internal`.

The CLI client uses plain blocking `socket` calls. Each CLI invocation sends one or a few requests, so asyncio would add nothing on the client side. `wait` polls `get` every 0.5 s rather than holding a server push stream, which keeps the protocol strictly request/response.

*Alternatives:* HTTP with FastAPI would duplicate the backend and add heavy dependencies. Unix sockets and named pipes need two transports and are poorly supported on Windows asyncio. gRPC is too heavy for a local tool.

### 3. Authentication and discovery: a token in a state file

On startup, the daemon generates `secrets.token_urlsafe(32)` and writes `<data_dir>/crawld.json` containing `{"pid", "port", "token", "started_at"}`. It writes atomically (temporary file, then `os.replace`). On POSIX the file mode is `0o600`. On Windows it relies on the per-user data directory's ACL. The daemon compares tokens with `hmac.compare_digest`. The CLI reads the file to find the port and token, so users never pass a port to client commands.

The data directory defaults to `%LOCALAPPDATA%\crawld` on Windows, `$XDG_STATE_HOME/crawld` (or `~/.local/state/crawld`) on Linux, and `~/Library/Application Support/crawld` on macOS. It is resolved with a small stdlib helper, which avoids a `platformdirs` dependency.

**Single instance and stale files.** At startup, if the state file exists, the daemon sends `ping` with its token. If that succeeds, it refuses to start. If the connection is refused or the token does not match, the file is stale and is replaced. The daemon removes the file on clean shutdown, in a `finally` block.

*Alternatives:* running with no auth was rejected, because any local process, including JavaScript in a browser posting to localhost, could submit crawls. A browser cannot speak raw TCP JSON-lines cleanly, but a token makes this explicit and is cheap. OS-level socket peer credentials are not portable.

### 4. Background start: re-spawn `crawld serve` detached

`crawld start` runs `subprocess.Popen([sys.executable, "-m", "crawl_daemon", "serve", ...])` with:
- **Windows:** `creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`.
- **POSIX:** `start_new_session=True`.

On both, stdin comes from `DEVNULL`, and stdout and stderr go to `<data_dir>/crawld.log`. The parent then polls for the state file plus a successful `ping` for up to 10 s. If the child exits first, the parent prints the tail of the log and exits non-zero.

`crawld stop` sends `shutdown`, then waits for the PID to disappear (polling `ping` until the connection is refused, then checking the process) for up to 30 s.

*Alternatives:* a double fork is POSIX-only. `python-daemon` is POSIX-only and adds a dependency.

### 5. Scheduling: one queue, N worker tasks

`JobScheduler` owns an `asyncio.Queue[str]` of job ids and `max_parallel_jobs` worker tasks. Each worker:
1. Takes an id from the queue.
2. Skips it if the job is no longer `queued`, for example because it was cancelled while waiting.
3. Marks it `running` with `started_at`.
4. Builds a `Crawler` with the daemon's three components (decision 8): a `SharedClientFetcher`, a `CachingParser` and a `StorageWriter`, all sharing one per-job `ParseCache`. The library's fallback components are never used.
5. Runs the crawl under `asyncio.Task` tracking, so it can be cancelled.
6. Records the final status, using the same rules as the backend's `CrawlService._run`: `seed_ok` decides `completed` or `failed`, `CancelledError` gives `cancelled`, and any other exception gives `failed` with `"{Type}: {message}"`.

The queue preserves FIFO order. Cancelling a queued job only updates its status, and the worker skips it later. That avoids having to remove items from the middle of an `asyncio.Queue`.

Submission validation is the same logic as the backend's `CrawlService.start`. Settings fill in defaults and enforce the limit checks, and `CrawlConfig` validates the rest. `ConfigError` and limit errors become `invalid_request`. This logic is about 30 lines and is copied, not shared (see Risks).

A single `httpx.AsyncClient` is shared by all jobs, through the `SharedClientFetcher` (decision 8). It is closed only after the scheduler has shut down.

**Shutdown:** stop accepting connections, cancel the worker tasks and wait for them (running jobs end `cancelled` and their writers flush), leave queued jobs untouched, close the HTTP client, close storage, and remove the state file. `serve` installs SIGINT and SIGTERM handlers on POSIX. On Windows it relies on `KeyboardInterrupt` and on the `shutdown` op.

**Recovery at startup:** `storage.mark_interrupted()` sets every `running` job to `failed` with "daemon stopped before the crawl finished". Then the scheduler enqueues every `queued` job in `submitted_at` order. Graceful shutdown never leaves a job `running`, so this only affects crashes.

### 6. Storage: one async `Storage` protocol, two implementations

```text
Storage
  open() / aclose()                     create the schema, check its version
  create_job(record) / get_job(id) / list_jobs(status?)
  update_job(id, **fields)              status, times, error, stats
  append_pages(job_id, pages)           batch: pages and distinct links
  read_pages(job_id, offset, limit) -> (pages, total)
  read_links(job_id, offset, limit) -> (links, total)
  mark_interrupted() -> int
  get_parsed_links(keys) -> dict[key, links]     parse cache lookup (batch-capable)
  put_parsed_links(entries)                      parse cache insert, ON CONFLICT DO NOTHING
```

**Schema (schema version 1, kept in a `meta` table):**
- `jobs(id TEXT PK, url, limits JSON, status, submitted_at, started_at, finished_at, error, pages, fetched, errors, robots_skipped, parse_cache_hits)`
- `parse_cache(key TEXT PK, links JSON, created_at)`. This table is shared by all jobs. `key` is a hex SHA-256 (see decision 8).
- `pages(job_id, seq INT, url, links JSON, PK(job_id, seq))`. A page's links are read as a whole and never queried one by one, so a JSON column avoids a third join table.
- `links(job_id, seq INT, url, PK(job_id, seq), UNIQUE(job_id, url))`. Distinct links are inserted with `INSERT ... ON CONFLICT (job_id, url) DO NOTHING`, which both databases support. `seq` comes from the writer, which numbers links it has not seen before. The writer keeps a per-job in-memory `set` of seen links, as the backend's `JobWriter` does, so most duplicates never reach SQL. The UNIQUE constraint is the backstop.

Timestamps are stored as ISO-8601 UTC text in SQLite and `timestamptz` in PostgreSQL. Limits are a JSON text column in SQLite and `jsonb` in PostgreSQL.

**SQLite (`SqliteStorage`):** uses stdlib `sqlite3` with one connection in WAL mode, owned by a dedicated single-thread `ThreadPoolExecutor`. Every call runs through `loop.run_in_executor(self._executor, ...)`. sqlite3 connections are thread-bound, so funnelling every call through one thread keeps it correct, and it serialises writes, which SQLite requires anyway. This needs no dependency (`aiosqlite` was rejected because it does the same thing as an extra dependency).

**PostgreSQL (`PostgresStorage`):** uses `psycopg` 3 with `psycopg_pool.AsyncConnectionPool` (min 1, max 4). The import happens lazily inside `open_storage`, and an `ImportError` becomes the "install `crawl-daemon[postgres]`" error. *Alternative:* `asyncpg` is faster, but it uses `$1` placeholders and its own type system, and psycopg is the more common default. SQL is written once with named parameters where the two dialects agree. A small per-dialect dictionary holds the few statements that differ: DDL types, and the `?` versus `%s` placeholder style.

**Contract tests:** one parametrised test module runs against SQLite (always) and PostgreSQL (when `CRAWLD_TEST_POSTGRES_URL` is set, otherwise skipped). This is how the "Both databases behave the same" requirement is verified. CI sets the variable with a `postgres:16` service container.

### 7. `StorageWriter`: buffered writes with a bounded flush delay

`StorageWriter(storage, job_id, stats)` implements the library's `Writer`. `write()` appends to an in-memory buffer and assigns page and link sequence numbers. The buffer is flushed with `append_pages` once it holds 50 pages, or 0.5 s after its oldest entry, whichever comes first. The time limit uses a timer task. Each flush also does two more things:
- It writes the live `stats` to the job row, including `parse_cache_hits` from the shared `ParseCache`.
- It drains the parse-cache entries waiting in the `ParseCache` with `put_parsed_links`. This happens in its own try/except: a cache write failure is logged and the entries are dropped, and it never fails the job.

`aclose()` flushes what is left.

The scheduler records the final status only after the crawl has returned, and the crawler always closes its writer first. That gives the spec's guarantee: all pages are stored by the time the final status is.

Batching matters because a crawl can report hundreds of pages a second, and one transaction per page would make SQLite the bottleneck. *Alternative:* writing every page in its own transaction is simpler, but it is measurably slow on SQLite with `synchronous=FULL`. With WAL, `synchronous=NORMAL` is used.

**Storage failure:** an exception from a flush propagates out of `write()` or `aclose()`, so the crawler stops (per `crawler-extension-api`, "Unexpected component errors stop the crawl"). The scheduler catches it and tries to record `failed` with the error. If that write also fails, it logs the error and moves on. Other jobs are unaffected, because each job has its own writer and its own task.

### 8. Crawler components: the daemon implements Fetcher, Parser and Writer

Every crawl gets three daemon-owned components that share one per-job `ParseCache`. `ParseCache` is a plain in-memory object with three parts: `prefetched: dict[key, links]`, `pending: list[(key, links)]` and `hits: int`.

- **`SharedClientFetcher`** wraps the library's `DefaultHttpxFetcher(client=shared_client)` for retries, body capping and error mapping. Its `aclose()` does nothing, because the client belongs to the daemon. This matches the backend's adapter. After a successful fetch of an HTML page (`result.is_html`), and only when the cache is enabled, it computes the cache key and awaits `storage.get_parsed_links([key])`. A hit is put in `ParseCache.prefetched`. Lookup errors are caught and logged, and the result is returned as is.
- **`CachingParser(inner=DefaultSelectolaxParser(), cache)`**:
  1. Computes the same key.
  2. If `prefetched` holds the key, it pops the entry, increments `hits` and returns the cached links.
  3. Otherwise it calls `inner.parse(page)`, appends `(key, links)` to `pending` and returns the links.
  4. If anything in the cache path raises, it falls back to `inner.parse(page)`.
  
  It never touches storage, so `parse` stays synchronous and never blocks the event loop on I/O.
- **`StorageWriter`** works as in decision 7, and also drains `pending` on each flush.

**Cache key:** `sha256(PARSER_VERSION + "\0" + final_url + "\0" + body)`. The parser's output depends on `final_url` (for `<base href>` joins) and on the body. `PARSER_VERSION` is a constant in `parser.py`, bumped when the inner parser or its configuration changes, so stale entries are never matched. The key is computed twice per page, once in the fetcher and once in the parser. SHA-256 over a body capped at a few MB costs microseconds to milliseconds, which is negligible next to the network fetch.

**Disabled cache:** with `CRAWLD_PARSE_CACHE=false`, the fetcher skips the lookup and the parser uses a `ParseCache` that discards `pending`. No reads or writes happen.

Cached links are the parser's raw output, before the crawler resolves and normalises them. So the crawler applies the same scope, de-duplication and normalisation rules to a cache hit as to a fresh parse, and the reported links are identical.

*Alternatives considered:*
- A synchronous database read inside `parse()`. It blocks the event loop on every page, which is acceptable for SQLite but not for a PostgreSQL round trip, and it needs a second, sync driver.
- Preloading the whole `parse_cache` table into memory at job start. Its memory use is unbounded and grows with every crawl.
- Making the library's `Parser` async. That is a breaking change to `crawler-extension-api`, outside this change's scope.
- Caching full responses in the fetcher. You asked for a fetcher like the backend's, and an HTTP cache raises freshness questions this change doesn't need to answer.

### 9. CLI: argparse subcommands with shared conventions

`build_parser()` defines the subparsers. The options shared by every subcommand (`--data-dir`, `--json`, `-v`) live on a parent parser. Crawl options reuse the `crawl` command's names and validators (`_positive_int` and `_non_negative_int` are re-implemented locally because they are private in the library). Exit codes are module constants, as in `site_crawler.cli`: 0 OK, 1 job failed, 2 usage, 3 not running, 4 not found, 5 conflict, 130 interrupted.

`pages` prints in the same layout as the library's `TextWriter` (URL, then the links indented by two spaces) by reusing `TextWriter` directly over the fetched `PageResult`s. `--all` pages through the results in batches of 500. Human-readable tables (`list`, `status`) use fixed-width columns with no dependency.

## Risks / Trade-offs

- **[The validation and running logic is copied from the backend, and the copies can drift]** → Both run against the same library, and each project's tests cover the shared rules (default budget, limit errors, seed failure gives `failed`). If a third consumer appears, move the shared job runner into the library.
- **[A localhost TCP port is reachable by every local user]** → The token in a user-only state file means another local user cannot use the daemon without reading that file. This is documented as a single-user tool and not hardened further.
- **[An interrupted crawl is lost, not resumed]** → It is marked `failed` with a clear message, and its partial pages are kept. The user can resubmit it. Persisting the frontier is a possible future change.
- **[Up to 0.5 s (or 50 pages) of results can be lost on a hard crash]** → Acceptable for a crawl that will be marked failed anyway. Graceful stops lose nothing.
- **[SQLite write contention with many parallel jobs]** → All writes go through one thread, in batches. The default of 2 parallel jobs is well within SQLite's limits. Users with heavy workloads can choose PostgreSQL.
- **[Detached process behaviour differs between platforms]** → Start and stop are covered by integration tests that spawn a real subprocess, and they run in CI on Linux. Windows is tested manually and noted in the README. The Windows-specific code is limited to `creationflags`.
- **[The `parse_cache` table grows without bound]** → Each entry is small: a key plus a JSON list of links. Pruning is listed as an open question, and the cache can be disabled.
- **[A parser change could serve stale cached links]** → `PARSER_VERSION` is part of the key. A test asserts the cache misses when the version differs.
- **[Two jobs parse the same new page at the same time]** → Both parse it and both queue an entry. `ON CONFLICT DO NOTHING` keeps one, and the results are identical, so this is harmless.
- **[Windows has no SIGTERM handling]** → `crawld stop` goes through the protocol instead of signals, so it shuts down cleanly on every platform. Only a hard kill skips cleanup, and recovery at startup handles that.

## Migration Plan

This adds a new project and changes no existing ones, so nothing needs migrating. The schema starts at version 1. Future schema changes bump the version and add forward migrations in `open()`. Older daemons refuse newer schemas, as specified. To roll back, delete `python/daemon/` and its CI job. User data in the data directory is left alone.

## Open Questions

- Should `crawld submit` also accept a file of URLs (one job per line)? It is easy to add later as a CLI-only feature.
- Should finished jobs be pruned automatically after a retention period? Deferred until there is real usage.
- Should `parse_cache` entries expire by age or by total size, or be pruned by a `crawld prune` command? The cache key never goes stale for correctness, so this only concerns disk use and can be decided later.
