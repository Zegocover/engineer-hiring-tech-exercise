# crawl-daemon

`crawld` runs [`site-crawler`](../README.md) crawls in the background. You submit a crawl job from a shell and get
your prompt back straight away. Jobs wait in a queue and a bounded number run at once. Their pages and links are
saved in a database as each crawl runs, so you can read them during the crawl, after it ends, and after the daemon
restarts.

Each job follows the same rules as the `crawl` command:

- It stays within the crawl scope (the base URL's host, plus any `--allow-host` patterns).
- It fetches each normalised URL once.
- It respects robots.txt unless you turn that off.

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/). The `site-crawler` library is installed from the parent
`python/` folder (`..`) as an editable path dependency.

```bash
cd python/daemon
uv sync                    # SQLite storage only
uv sync --extra postgres   # also PostgreSQL storage (installs psycopg)
```

Then run commands with `uv run crawld ...`, or activate the virtual environment and use `crawld` directly.

## Walkthrough

```console
$ crawld start
crawld started (pid 41872, port 8765)

$ crawld submit https://books.toscrape.com/ --max-pages 50
5f0c2b9e4d1a4c33a7e0d2c1b8f6e9aa

$ crawld list
ID                                STATUS     PAGES  ERRORS  SUBMITTED            URL
5f0c2b9e4d1a4c33a7e0d2c1b8f6e9aa  running       12       0  2026-10-15 09:12:03  https://books.toscrape.com/

$ crawld wait 5f0c2b9e4d1a4c33a7e0d2c1b8f6e9aa
running: 31 pages (31 fetched, 0 errors, 0 blocked by robots.txt, 0 from the parse cache)
completed: 50 pages (50 fetched, 0 errors, 0 blocked by robots.txt, 0 from the parse cache)

$ crawld pages 5f0c2b9e4d1a4c33a7e0d2c1b8f6e9aa --limit 1
https://books.toscrape.com/
  https://books.toscrape.com/index.html
  https://books.toscrape.com/catalogue/category/books_1/index.html
  ...

$ crawld stop
crawld stopped
```

`crawld submit URL --wait` submits a job and waits for it in one step. Progress goes to stderr, so
`crawld pages ID --all > pages.txt` gives you just the results. Pressing Ctrl+C while waiting stops the wait, not
the job.

## Commands

| Command | What it does |
|---|---|
| `crawld serve` | Run the daemon in the foreground, logging to stderr. Stop it with Ctrl+C. |
| `crawld start` | Start the daemon in the background, logging to `crawld.log` in the data directory. Returns once the daemon is accepting jobs. |
| `crawld stop` | Stop the daemon. Running jobs end as `cancelled`; queued jobs stay queued and run after the next start. |
| `crawld ping` | Say whether the daemon is running, with its port and the number of running and queued jobs. |
| `crawld submit URL` | Submit a job and print its id. Options: `--max-pages`, `--max-depth`, `-c/--concurrency`, `--per-host-concurrency`, `--allow-host PATTERN` (repeatable), `--no-robots`, `--wait`. |
| `crawld wait ID` | Show a job's progress until it finishes. |
| `crawld list [--status S]` | List jobs, newest first. |
| `crawld status ID` | Show a job's details: limits, times, statistics and error. |
| `crawld pages ID` | Print a job's pages, each followed by its links, in the same layout as the `crawl` command. Use `--offset` and `--limit` (100 by default) for a slice, or `--all` for every page. |
| `crawld links ID` | Print a job's distinct links in the order they were first found, including links that weren't followed. Takes the same options as `pages`. |
| `crawld cancel ID` | Cancel a queued or running job. A running job keeps the pages it had already found. |

Every command takes `--data-dir`. `serve` and `start` also take `--port`, `--database`, `--max-parallel-jobs`,
`--no-parse-cache` and `--log-level`. Every command except `serve`, `start` and `stop` takes `--json`. With it, the
command prints one JSON document; with `pages --all` or `links --all`, it prints one JSON value per line.

A job is `queued`, `running`, `completed`, `failed` or `cancelled`. A job fails when its base URL can't be fetched
or when it hits an unexpected error, such as a database failure, and `crawld status` shows why. If other pages fail,
they're counted as errors and the job still completes. If the daemon process is killed, the jobs it was running are
marked `failed` on the next start ("the daemon stopped before the crawl finished") and keep the pages they had found.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success. |
| 1 | A waited-on job failed or was cancelled, or the daemon couldn't start or stop. |
| 2 | Usage error, or the daemon rejected the request (e.g. a non-HTTP URL or a page budget above the maximum). |
| 3 | The daemon isn't running. |
| 4 | No job with that id. |
| 5 | Conflict, e.g. cancelling a job that has already finished. |
| 130 | Interrupted with Ctrl+C. |

## Settings

Every setting can come from a `CRAWLD_*` environment variable. The `serve` and `start` options override them.

| Variable | Default | Meaning |
|---|---|---|
| `CRAWLD_DATA_DIR` | see below | State file, log and default database. |
| `CRAWLD_PORT` | `8765` | Loopback port to listen on; `0` picks a free one. |
| `CRAWLD_DATABASE_URL` | `crawld.db` in the data dir | `sqlite:///PATH` or `postgresql://user:pass@host/db`. |
| `CRAWLD_MAX_PARALLEL_JOBS` | `2` | Jobs that run at once; the rest wait as `queued`. |
| `CRAWLD_PARSE_CACHE` | `true` | Reuse links parsed from identical pages (see below). |
| `CRAWLD_DEFAULT_MAX_PAGES` | `1000` | Page budget for a job that doesn't set one. |
| `CRAWLD_MAX_PAGES_LIMIT` | `10000` | Largest page budget a job may ask for. |
| `CRAWLD_DEFAULT_CONCURRENCY` | `8` | Parallel requests for a job that doesn't set them. |
| `CRAWLD_MAX_CONCURRENCY` | `32` | Largest concurrency (or per-host concurrency) a job may ask for. |
| `CRAWLD_MAX_CONNECTIONS` | `100` | HTTP connections shared by all jobs. |
| `CRAWLD_REQUEST_TIMEOUT` | `10` | Per-request timeout in seconds. |
| `CRAWLD_USER_AGENT` | `site-crawler/0.1 ...` | User-Agent header. |

The data directory is `%LOCALAPPDATA%\crawld` on Windows, `~/Library/Application Support/crawld` on macOS and
`$XDG_STATE_HOME/crawld` (by default `~/.local/state/crawld`) elsewhere. To run more than one daemon, give each its
own data directory and port. Client commands find the daemon through the data directory, so pass the same
`--data-dir` to them.

## How it works

```
crawld submit ... --> JSON lines over 127.0.0.1 --> daemon --> FIFO queue --> N workers --> Crawler
                      (token from the state file)                                           |
                                                       SharedClientFetcher, CachingParser, StorageWriter
                                                                         |
                                                              SQLite or PostgreSQL
```

- **Connection.** The daemon listens on `127.0.0.1` only and speaks newline-delimited JSON. Each time it starts,
  it writes `crawld.json` to its data directory with its port, process id and a new random token. On POSIX, only
  you can read that file. Client commands read it to find the daemon, and every request must carry the token.
- **Crawler components.** The daemon provides its own fetcher, parser and writer, through the library's extension
  points, to every job:
  - `SharedClientFetcher` fetches through one `httpx` connection pool shared by all jobs.
  - `CachingParser` wraps the library's HTML parser with the parse cache.
  - `StorageWriter` stores pages, and the distinct links found on them, in batches. A batch is written once it
    holds 50 pages or half a second after its first page, whichever comes first.
- **Parse cache.** The links parsed from a page are stored, keyed by a hash of the parser version, the page's
  final URL and its body. Crawling an unchanged page again, in any later job and even after a restart, reuses them
  instead of parsing again, and `crawld status` counts these as "from the parse cache". The library's parser
  interface is synchronous, so the fetcher looks pages up in the cache while it is still async, and the parser only
  reads memory. If the cache fails, the page is just parsed. `--no-parse-cache` turns the cache off.
- **Storage.** SQLite needs nothing extra. PostgreSQL needs the `postgres` extra. The daemon creates the tables it
  needs on startup, and refuses to use a database whose schema is newer than it understands.

**Security.** `crawld` is meant for one local user. It accepts only loopback connections that carry its token,
but it is not hardened for exposure to a network.

## Development

```bash
uv sync --all-extras
uv run pytest           # tests (no network: in-memory sites, respx, local sockets)
uv run mypy             # strict type checking
uv run ruff check       # lint
uv run ruff format      # format
```

The storage tests also run against PostgreSQL when `CRAWLD_TEST_POSTGRES_URL` is set; CI sets it. For example:

```bash
docker run -d --name crawld-pg -e POSTGRES_PASSWORD=crawld -p 127.0.0.1:15433:5432 postgres:16
CRAWLD_TEST_POSTGRES_URL=postgresql://postgres:crawld@127.0.0.1:15433/postgres uv run pytest
```

On Windows the daemon runs on asyncio's selector event loop, because psycopg's async mode can't use the default
Proactor loop.
