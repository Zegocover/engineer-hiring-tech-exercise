# Web Crawler

A fast, async web crawler CLI tool built with Python.

> **Note:** The original test requirements can be found in [docs/TASK.md](docs/TASK.md)

## Quick Start

```bash
# Install dependencies
uv venv && uv pip install -e ".[dev]"

# Activate virtual environment
source .venv/bin/activate

# Run the crawler
crawl https://example.com

# With options
crawl https://example.com --concurrency 20 --max-pages 100

# Run tests
pytest tests/ -v
```

## CLI Usage

```
crawl [-h] [-c CONCURRENCY] [-t TIMEOUT] [-m MAX_PAGES] [-v] [-q] url

positional arguments:
  url                   Base URL to start crawling from

options:
  -c, --concurrency     Maximum concurrent requests (default: 10)
  -t, --timeout         Request timeout in seconds (default: 30)
  -m, --max-pages       Maximum pages to crawl (default: unlimited)
  -v, --verbose         Enable debug logging
  -q, --quiet           Output only URLs, no formatting
```

---

# Design Decisions

## Architecture Overview

The crawler is structured as three distinct modules with clear separation of concerns:

```
src/crawler/
├── url_utils.py    # URL normalization, validation, filtering
├── parser.py       # HTML parsing and link extraction
├── crawler.py      # Async BFS engine with concurrency control
└── __main__.py     # CLI interface
```

## Key Design Decisions

### 1. Search Strategy: BFS over DFS

**Decision:** Breadth-First Search with async workers

**Options Considered:**
| Strategy | Parallelism | Memory | Suitability |
|----------|-------------|--------|-------------|
| DFS | Poor - sequential | Low | Not suitable for async |
| BFS | Excellent - batch at each level | Moderate | Perfect for concurrent I/O |
| Hybrid/Priority | Good | Variable | Over-engineered for this scope |

**Rationale:**
- BFS naturally allows fetching N URLs concurrently at each "level"
- Important pages (navigation, main content) are typically close to root
- Natural fit for `asyncio.Queue` + semaphore pattern
- Easy to implement depth limiting if needed

### 2. Concurrency Model: Async with Semaphore

**Decision:** `aiohttp` with `asyncio.Semaphore` for rate limiting

**Options Considered:**
| Approach | Pros | Cons |
|----------|------|------|
| Threading + requests | Simple mental model | GIL limits true parallelism |
| Multiprocessing | True parallelism | High memory, complex IPC |
| Async + aiohttp | Efficient I/O, scalable | Slightly complex error handling |

**Rationale:**
- Web crawling is I/O-bound, not CPU-bound
- Async handles thousands of concurrent connections efficiently
- Semaphore prevents overwhelming target servers
- Connection pooling reduces TCP overhead

### 3. URL Normalization Strategy

**Decision:** Strict canonicalization before deduplication

**Normalization steps:**
1. Resolve relative URLs against base
2. Lowercase scheme and host
3. Remove fragment identifiers (`#section`)
4. Normalize empty path to `/`
5. Remove trailing slashes (except root)

**Trade-off:** We chose correctness over permissiveness. Two URLs that look different but resolve to the same content should be treated as one.

### 4. Domain Matching: Strict Single Domain

**Decision:** Exact domain match only (subdomains excluded)

**Example:**
- `example.com` ✓ crawled
- `www.example.com` ✗ not crawled (different subdomain)
- `blog.example.com` ✗ not crawled

**Rationale:** Per requirements, the crawler should "only process that single domain and not crawl URLs pointing to other domains or subdomains." This is the conservative interpretation.

**Alternative considered:** Treat `www.` as equivalent to bare domain. Decided against to maintain strict compliance with requirements.

### 5. Error Handling: Log and Continue

**Decision:** Errors are logged but don't stop the crawl

| Error Type | Handling |
|------------|----------|
| HTTP 4xx/5xx | Log warning, return empty links |
| Timeout | Log warning, skip page |
| Connection error | Log warning, skip page |
| Parse error | Log warning, return empty links |

**Rationale:** A production crawler should be resilient. One failing page shouldn't prevent crawling the rest of the site.

### 6. Output Format: Streaming with Callback

**Decision:** Print results as pages are crawled, not after completion

**Rationale:**
- Provides immediate feedback on progress
- Works well for large sites (no memory accumulation)
- Allows piping to other tools (`crawl https://site.com | grep pattern`)

---

## Trade-offs Made

### Simplicity vs Robustness

| Chose Simplicity | Could Have Added |
|------------------|------------------|
| No retry logic | Exponential backoff on failures |
| No robots.txt | robots.txt parsing and respect |
| No rate limiting | Configurable delay between requests |
| No sitemap.xml | Sitemap parsing for faster discovery |

**Rationale:** These features add complexity. The core requirement is a working crawler demonstrating good design, not a production-ready tool.

### Memory vs Speed

| Decision | Trade-off |
|----------|-----------|
| Store all visited URLs in memory | Fast O(1) lookup, but memory grows with site size |
| Store all results for summary | Enables statistics, but large sites could exhaust memory |

**Mitigation:** Added `--max-pages` flag to cap memory usage on large sites.

### Strict vs Permissive Parsing

| Decision | Trade-off |
|----------|-----------|
| Skip non-HTTP schemes | May miss legitimate `//example.com` protocol-relative URLs |
| Skip binary extensions | May miss HTML pages with unusual extensions |
| lxml parser | Fastest, but may parse differently than browsers |

---

## What I Would Add With More Time

### High Priority

1. **Retry with exponential backoff** - Handle transient failures gracefully
2. **robots.txt support** - Respect site policies
3. **Depth limiting** (`--max-depth`) - Control crawl scope
4. **JSON output format** - For programmatic consumption

### Medium Priority

5. **Sitemap.xml parsing** - Faster discovery of all pages
6. **Rate limiting** - Configurable delay to avoid overwhelming servers
7. **Progress bar** - Visual feedback for long crawls
8. **Resume capability** - Save state and continue interrupted crawls

### Lower Priority

9. **Multiple domain support** - Crawl several sites in parallel
10. **Database storage** - Persist results for large crawls
11. **Web UI** - Alternative to CLI for complex configurations
12. **Distributed crawling** - Scale across multiple machines

---

## Tools Used

### Development Environment

- **IDE:** VSCode with Python extensions
- **AI Assistant:** Claude Code (Anthropic) - used for planning, implementation guidance, and code review
- **Package Manager:** uv (fast Python package installer)
- **Python Version:** 3.12

### Dependencies

| Library | Purpose | Why Chosen |
|---------|---------|------------|
| aiohttp | Async HTTP client | Fast, mature, connection pooling |
| beautifulsoup4 | HTML parsing | Robust, handles malformed HTML |
| lxml | Parser backend | Fastest parser available |

### Testing & Quality

| Tool | Purpose |
|------|---------|
| pytest | Test framework |
| pytest-asyncio | Async test support |
| aioresponses | Mock HTTP responses |
| mypy | Static type checking |
| ruff | Linting and formatting |

---

## Project Structure

```
python/
├── src/crawler/
│   ├── __init__.py
│   ├── __main__.py      # CLI entry point
│   ├── crawler.py       # Main async crawler
│   ├── parser.py        # HTML link extraction
│   └── url_utils.py     # URL utilities
├── tests/
│   ├── test_crawler.py  # Integration tests
│   ├── test_parser.py   # Parser unit tests
│   └── test_url_utils.py # URL utils unit tests
├── docs/
│   ├── TASK.md          # Original test requirements
│   ├── PLAN.md          # Initial planning document
│   ├── PLAN_v2.md       # Detailed design with BFS analysis
│   ├── PROMPTS.md       # AI prompts used during development
│   └── REVIEWS.md       # Code review checkpoints
├── pyproject.toml       # Project configuration
└── README.md            # This file
```

## Test Coverage

```
76 tests covering:
- URL normalization edge cases
- Domain matching rules
- Link extraction from various HTML
- Async crawler behavior
- Error handling
- Configuration options
```

---

## Extending for Multiple Domains

If extending to crawl multiple domains simultaneously:

### CLI Limitations

A CLI interface becomes unwieldy:
```bash
# This gets messy
crawl https://site1.com https://site2.com https://site3.com --config site1:depth=5,site2:depth=3
```

### Better Alternatives

1. **Configuration file (YAML/TOML)**
```yaml
targets:
  - url: https://site1.com
    max_depth: 5
    concurrency: 10
  - url: https://site2.com
    max_depth: 3
    concurrency: 5
```

2. **Web API**
```python
POST /crawl
{
  "targets": ["https://site1.com", "https://site2.com"],
  "config": {"concurrency": 20}
}
```

3. **Message Queue Integration**
- Submit URLs to RabbitMQ/Redis
- Workers pick up and crawl
- Results stored in database
- Scales horizontally

### Architecture Changes Needed

- **Shared state management** - Redis/database for visited URLs across workers
- **Result aggregation** - Central storage for results
- **Orchestration** - Coordinator to manage multiple crawl jobs
- **Monitoring** - Dashboard for crawl progress and health
