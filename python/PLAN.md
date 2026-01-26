# Plan

## Table of contents
- [Goals](#goals)
- [Constraints](#constraints)
- [Decisions (with rationale)](#decisions-with-rationale)
- [Requirements (MoSCoW)](#requirements-moscow)
- [Crawler considerations](#crawler-considerations)
- [Defaults](#defaults)
- [Steps](#steps)
  - [Step 1: CLI interface and configuration](#step-1-cli-interface-and-configuration)
  - [Step 2: URL scoping, retention, and deduping](#step-2-url-scoping-retention-and-deduping)
  - [Step 3: Async fetcher, concurrency, and redirects](#step-3-async-fetcher-concurrency-and-redirects)
  - [Step 4: HTML parsing and link extraction](#step-4-html-parsing-and-link-extraction)
  - [Step 5: Output renderers](#step-5-output-renderers)
  - [Step 6: Tests](#step-6-tests)
  - [Step 7: Documentation and trade-offs](#step-7-documentation-and-trade-offs)
- [Glossary](#glossary)

## Goals
- Build a fast, single-domain web crawler CLI in Python (no Scrapy/Playwright).
- Print each visited page URL and the URLs found on that page.
- Include tests, documentation, and a design discussion in the README.

## Constraints
- No Scrapy or Playwright (per prompt).
- Single-domain crawl scope (exact host only).
- No JS rendering; only server-rendered HTML.

## Decisions (with rationale)
### Python
**Decision:** target Python 3.13+.  
**Rationale:** use the latest stable runtime and note compatibility in README.

### Dependencies
**Decision:** use `uv` with `pyproject.toml` and a lockfile.  
**Rationale:** fast installs and a simple workflow without Poetry’s heavier surface area.

### Concurrency and HTTP client
**Decision:** use `asyncio` with `aiohttp`.  
**Rationale:** crawling is I/O-bound; one event loop scales well and simplifies backpressure/rate limiting; `aiohttp` avoids thread overhead.

### Scope and URL handling
**Decision:** scope by exact host only (no subdomains).  
**Rationale:** matches the prompt requirement to exclude subdomains.

**Decision:** retain query strings, strip fragments by default, and normalise trailing slashes for dedupe.  
**Rationale:** query strings can be page-specific, fragments are typically in-page anchors, and trailing slashes are normalised to reduce duplicates.

### Robots and redirects
**Decision:** read `robots.txt` with a respect/ignore flag.  
**Rationale:** polite by default but configurable.

**Decision:** follow redirects only if target is in-scope.  
**Rationale:** prevents accidental cross-domain crawling.

### Parsing
**Decision:** BeautifulSoup with `lxml`.  
**Rationale:** faster than html5lib while robust enough for real-world HTML.

**Decision:** extract only `a[href]`.  
**Rationale:** limit to navigation links; avoid assets and metadata URLs.

### Output
**Decision:** default text file output; optional JSON via renderers.  
**Rationale:** simple default with an extensible interface.

**Decision:** stream outputs.  
**Rationale:** avoids large in-memory buffers on bigger crawls.

**Note:** per-link logging is currently at INFO for visibility; consider downgrading to DEBUG or gating behind `--verbose` if logs become too noisy.

### Code style and linting
**Decision:** use Black for formatting and Ruff for linting.  
**Rationale:** standard, fast tooling aligned with PEP 8.

## Requirements (MoSCoW)
[MoSCoW method](https://en.wikipedia.org/wiki/MoSCoW_method)
### Must have
- CLI accepts a base URL and crawls within allowed host scope (exact host).
- For each page, print the page URL and the URLs found on that page.
- Provide a `--profile` flag that selects crawl presets (default: `balanced`).
- Deduplicate URLs and avoid revisiting pages.
- Unit tests for URL scoping, normalization rules, and link extraction.
- Plan includes design decisions, trade-offs, and tooling/AI usage.

### Should have
- JSON file output option via a renderer interface.
- Respect or ignore `robots.txt` via a user flag.
- Configurable limits: max concurrency, timeouts, max pages/depth.
- Handle 429s with cooldown/backoff behaviour.
- Follow redirects only when target stays in-scope.
- Parse only HTML content types; ignore binary/non-HTML.
- Verbose logging flag for more detailed progress output.

### Could have
- Retry/backoff for transient network errors.
- Concurrency with global rate limiting/backpressure.
- Sitemap discovery/usage.
- Per-path crawl delay tuning.
- Output an aggregated, unique list of all links found at the end of the crawl.
- Flags to control output link filtering (strip fragments, only http, only in-scope).
- Move output writing to a dedicated writer queue/task to avoid blocking workers.

### Won't have (for this submission)
- JS rendering or headless browser support (prompt disallows Playwright).
- Multi-domain crawling (documented as an extension).
- Distributed crawling or resumable state (e.g., persisting queue/visited set to resume a crawl).
- HEAD preflight requests before GET (adds extra round trips and is unreliable on some servers).

## Crawler considerations
- 429 handling: honor `Retry-After` when present and apply retry backoff with capped attempts.
- JS-rendered pages: the prompt excludes Playwright, so we assume JS rendering is out of scope; only server-rendered HTML is parsed. Note future extension: optional headless renderer or prerender service.
- Content types: only parse `text/html`; skip binary or non-HTML responses.
- Redirects: only follow redirects if the target remains within the allowed domain scope.
- Politeness: configurable timeouts, max concurrency, and user-agent; optional crawl delay if needed.
- Robots: fetch robots.txt for the base host only.

## Defaults
- Provide a `--profile` flag with presets: `conservative`, `balanced` (default), `aggressive`.
- Each profile sets max pages, max depth, concurrency, and timeouts.

| Profile | Max pages (crawled) | Max depth | Concurrency | Timeout | Max attempts |
| --- | --- | --- | --- | --- | --- |
| conservative | 500 | 3 | 10 | 10s | 3 |
| balanced | 2,000 | 5 | 25 | 10s | 3 |
| aggressive | 10,000 | 8 | 50 | 8s | 3 |

## Steps

### Step 1: CLI interface and configuration
### Command
- `crawler <base_url> [options]`

### Required
- `base_url`: starting URL (http/https).

### Profiles
- `--profile {conservative,balanced,aggressive}` (default: `balanced`)

### Output
- `--output {text,json}` (default: `text`)
- `--output-file <path>` optional; defaults to `output.txt` or `output.json` based on format.
- Always emit progress/logging to stdout; output content goes to the file (defaulting to `output.txt`/`output.json` when not specified).

### Robots
- `--robots {respect,ignore}` (default: `respect`)

### Other
- `--user-agent <string>` (default: `crawler/1.0`)

### Step 2: URL scoping, retention, and deduping
### Scope rules
- Only crawl URLs whose host matches the base URL host exactly.
- Accept only `http` and `https` schemes.

### Retention rules
- Keep query strings.
- Strip fragments by default (configurable via `--strip-fragments`).
- Normalise trailing slashes for dedupe.

### Normalization (for dedupe only)
- Lowercase scheme and host.
- Remove default ports (80 for http, 443 for https).
- Resolve relative URLs against the page URL.
- Keep scheme in the normalized key (http/https treated as distinct).

### Deduping
- Maintain a visited set on normalized URLs; enqueue only if not seen.
- Output the normalised page URL for reporting.

### Step 3: Async fetcher, concurrency, and redirects
### Fetching
- Use `aiohttp` with a shared `ClientSession`.
- Respect timeouts (profile-defined) and set a clear `User-Agent`.

### Concurrency
- Use a global semaphore for in-flight requests, sized by the profile.

### Redirects
- Follow redirects only if the target URL remains in-scope (exact host).
- If redirect target is out-of-scope, treat as terminal and do not enqueue.

### Queueing and dedupe (trade-offs)
- **Option A (lock-based):** workers check+add to a shared `visited` set with an `asyncio.Lock`, and enqueue new URLs directly. Simple, low overhead, but adds a lock in the hot path.
- **Option B (single scheduler, chosen):** workers emit discovered URLs to a candidates queue; one scheduler coroutine does dedupe and enqueues crawl tasks. Avoids locks and centralizes dedupe/backpressure, at the cost of an extra queue and coroutine.

### TODOs (scheduler/backpressure)
- Decide how to signal shutdown (sentinel vs cancellation).
- Add max_pages_crawled enforcement (stop scheduling after limit).
- Add backpressure controls (queue sizes, fetcher coordination).
- Ensure the worker resolves links before enqueueing candidates.
- Handle scheduler shutdown when max_pages_crawled is reached.
- Handle termination when there is nothing left to schedule.
- Enforce max_pages_crawled in the worker based on pages successfully fetched.

### Step 4: HTML parsing and link extraction
### Content-type gate
- Only parse responses where `Content-Type` includes `text/html`.
- Acknowledge this may miss misconfigured servers, but keeps the crawler focused and efficient.

### Parsing and extraction
- Use BeautifulSoup with the `lxml` parser (faster than html5lib while remaining robust). Benchmark source: [Parsing HTML - Art of Web Scraping](https://aows.jpt.sh/parsing/).
- Extract links only from `a[href]`; explicitly ignore `link[href]`, `img[src]`, and other non-navigation URLs.
- Resolve relative URLs against the page URL before scoping/deduping.

### Step 5: Output renderers
### Renderer interface
- Define a small interface, e.g., `Renderer.write_page(page_url, links)` and `Renderer.close()`.
- Implement `TextRenderer` and `JsonRenderer`.
- Stream output for both text and JSON to avoid large in-memory buffers (write incrementally as pages are processed).
- Monitor throughput to ensure the scheduler/dedupe loop (the "dispatcher") does not become a bottleneck; if needed, consider moving file writes off the hot path (e.g., a writer task/thread).
- Flush periodically to keep progress visible.

### Output formats
- Text: grouped by page, with the page URL followed by an indented list of discovered links.
- JSON: streamed array of objects with `{ "page_url": "...", "links": ["...", "..."] }`.

Example (text):
```
https://example.com/
  - https://example.com/about
  - https://example.com/contact
```

Example (json):
```
[
  {
    "page_url": "https://example.com/",
    "links": [
      "https://example.com/about",
      "https://example.com/contact"
    ]
  }
]
```

### Step 6: Tests
- Use `pytest` with a `tests/` directory at the repo root.
- Include async tests with `pytest-asyncio`.
- Mock HTTP responses for the crawl loop (e.g., `aioresponses` for `aiohttp`).
- Focus on URL scoping/normalization, link extraction, and renderer outputs.

### Step 7: Documentation and trade-offs
- Capture decisions and trade-offs directly in this plan (kept concise).
- Note prompt-driven constraints (e.g., no Playwright) and their implications.
- List extensions if time allowed (multi-domain, robots, sitemaps, persistent state).

## Glossary
- **Exact host:** only URLs whose hostname matches the base URL hostname (case-insensitive) are in-scope.
- **MoSCoW:** Prioritization method: Must have, Should have, Could have, Won’t have. See the linked MoSCoW method reference above.
