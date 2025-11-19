## Usage

Run the crawler from the repository root.

Create and activate a venv (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r web_crawler/requirements.txt
```

Run the CLI (polite defaults):

Run the package as a module (recommended when running from source or after an editable install):

```bash
PYTHONPATH=. python -m web_crawler https://example.com --max-pages 20 --concurrency 6
```

Or run the bundled CLI script directly (from the repository root):

```bash
python3 web_crawler/web_crawler.py https://example.com --max-pages 20 --concurrency 6
```


**CLI Options**

- **`base_url`**: Positional argument. The starting URL for the crawl (required). Must be an absolute `http://` or `https://` URL with a hostname.
- **`--concurrency`, `-c`**: Number of concurrent fetch workers (default: `10`).
- **`--max-pages`**: Maximum number of pages to fetch before stopping the crawl (default: `100`).
- **`--max-depth`**: Maximum link-following depth from the start URL (default: no limit).
- **`--timeout`**: Per-request timeout in seconds (default: `10`).
- **`--user-agent`**: User-Agent string used for requests (default: `web-crawler-exercise/1.0`).
- **`--ignore-robots-txt`**: Boolean flag. When set, the crawler will ignore `robots.txt` rules for the target host.
- **`--ignore-crawl-delay`**: Boolean flag. When set, the crawler will ignore any `Crawl-delay` directive in `robots.txt`.
- **`--no-strip-tracking-params`**: Boolean flag. When set, the crawler will NOT strip common tracking query parameters from URLs (by default tracking params are stripped).
- **`--verbose`**: Boolean flag. Enable more verbose logging output from the crawler.

Note:
- Pick conservative values for `--concurrency` and `--max-pages` when doing live runs to avoid overloading targets.

**Verbose output example**

When `--verbose` is enabled the crawler prints extra info like request durations, retry messages, and a crawl summary to the console. Example output:

```text
Visited: https://example.com (0.34s)
Links:
 - https://example.com/about
 - https://example.com/contact
[DELAY] waiting 1.00s for example.com
Retry 1 for https://example.com/about due to HTTP 502
Retry 2 for https://example.com/about due to HTTP 502
Visited: https://example.com/contact (0.21s)
---- Crawl summary ----
Time: 3.12s, Pages visited: 4, Requests: 6
Success: 4, Fail: 0, Retries: 2
Bytes: 12345, Avg req: 0.29s, Pages/sec: 1.28
```

## Tests

Deterministic unit and integration tests are under `web_crawler/tests/`. They use an in-process `aiohttp` test server and are designed to run offline.

Run all tests in the package (inside the venv):

```bash
PYTHONPATH=. python -m pytest web_crawler/tests -q
```

Live network tests are opt-in and will not run unless enabled. The CLI option `--live-target` accepts the live target URL as its value and will enable any tests marked `live`:

```bash
PYTHONPATH=. python -m pytest web_crawler/tests -q -m live --live-target="https://example.com"
```

Or run both local tests and live tests together:

```bash
PYTHONPATH=. python -m pytest web_crawler/tests -q --live-target="https://example.com"
```

Note:
- Live tests perform real network requests and can be slow or flaky.


## Design summary

- **Core**: `WebCrawler` implemented in `web_crawler/src/web_crawler.py` (exposed as the `web_crawler` package). A small launcher script lives at `web_crawler/web_crawler.py` and the module entrypoint supports `python -m web_crawler`.
- **Politeness**: honors `robots.txt` and `Crawl-delay` by default; flags `--ignore-robots-txt` and `--ignore-crawl-delay` override.
- **Limits**: supports `--max-pages` (default 100) and `--max-depth`; crawler stops scheduling when either is reached.
- **Normalization**: canonical handling, deduplication, tracking-parameter stripping (opt-out with `--no-strip-tracking-params`).
- **Tracking** params: by default the crawler strips a set of common tracking query parameters (for example `utm_*`, `gclid`, `fbclid`, `_ga`, `_gid`, etc.) to avoid duplicative URLs. You can disable stripping entirely with `--no-strip-tracking-params`. When using the `WebCrawler` class programmatically you can customize behaviour via the `tracking_blacklist` and `tracking_whitelist` constructor arguments — the blacklist lists parameters that are removed by default, while the whitelist (if provided) preserves specific parameters even if they match common tracking names.
- **Concurrency & timeouts**: the crawler uses an adjustable worker pool (`--concurrency`, default `10`) to control parallel fetches and a per-request `--timeout` (default `10` seconds). These settings let you tune throughput versus politeness and failure sensitivity when running against live targets.
- **Connection pooling**: the crawler reuses an `aiohttp.TCPConnector` (connection pool) for all requests to reduce TCP/TLS handshakes and DNS lookups. Conservative defaults are used (`limit = max(100, concurrency*2)`, `limit_per_host = max(10, concurrency)`, DNS cache TTL 300s), but these can be tuned if you need higher throughput. Exposing connector limits as CLI flags (for example `--connector-limit` and `--limit-per-host`) is straightforward and can be added for explicit tuning knobs. - **Retrying/backoff**: the crawler treats transient failures (network exceptions and HTTP 5xx responses) as retryable. It attempts up to 2 retries (3 attempts total) per request, using exponential backoff starting at 0.5s and doubling each retry (0.5s, 1s, ...). Retries increment the crawler's `retry_count` metric and are logged when `--verbose` is enabled. CLI flags to configure retry/backoff behaviour were considered, and decided to be out of scope for this release
- **Verbose output**: when `--verbose` is set the crawler prints progress for each visited page (including per-request duration), discovered links, crawl-delay waits, retry attempts, and a final crawl summary with metrics (pages visited, requests, successes, failures, retries, bytes fetched, average request duration).
- **Testing**: deterministic integration tests use `aiohttp` test server fixture; live tests are gated and opt-in.


**Extending: multi-domain crawling**

The current crawler restricts scheduling to the same host as the start URL to keep behaviour simple. To extend the crawler to support multi-domain crawling whilst keeping the command line interface, we can consider the following changes:

- **Per-host queues and semaphores:** maintain a frontier and an asyncio.Semaphore per host (or a small pool of worker tasks per host) so you can enforce per-host concurrency and crawl-delay separately.
- **Robots & crawl-delay:** fetch and cache `robots.txt` for each host and enforce its `Disallow` and `Crawl-delay` directives independently (the existing `RobotsParser` can be reused per-host).
- **Global de-duplication:** keep a global `visited` set or centralized URL index to avoid revisiting the same URL across hosts while still allowing per-host scheduling.
- **Politeness & rate-limiting:** choose conservative per-host concurrency and apply rate limits to avoid overloading smaller domains; consider making per-host delays configurable.
- **Scheduling & prioritization:** implement a scheduler that picks work from multiple per-host queues (round-robin or weighted by priority) so one noisy host doesn't starve others.
- **Storage & limits:** update max-pages semantics (global vs per-host), and persist discovered URLs or use a polite backoff strategy when encountering many transient errors.
- **Logging:** consider JSON output, or interleave output from hosts: 

```text
[2025-11-19T12:34:56.789Z] example.com  INFO Visited: https://example.com (0.32s)
[2025-11-19T12:34:56.801Z] other.org    INFO Visited: https://other.org/ (0.21s)
[2025-11-19T12:34:57.200Z] example.com  INFO [DELAY] waiting 1.00s for example.com
[2025-11-19T12:34:57.350Z] other.org    INFO Retry 1 for https://other.org/api due to HTTP 502
[2025-11-19T12:34:57.900Z] example.com  INFO Visited: https://example.com/about (0.25s)
---- Per-host summary: example.com ----
Pages: 4, Requests: 6, Success: 4, Fail: 0, Retries: 2, Avg req: 0.29s
---- Per-host summary: other.org ----
Pages: 8, Requests: 9, Success: 8, Fail: 0, Retries: 1, Avg req: 0.18s
---- Global summary ----
Pages visited: 12, Requests: 15, Success: 12, Fail: 0, Retries: 3
```

If we extend to a graphical user interface with the capability to print the output for multiple domains simultaneously, we can consider switching to an event-based model, where the crawler emits events for the UI to aggregate.