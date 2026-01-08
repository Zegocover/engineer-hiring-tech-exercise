# Web Crawler Implementation Plan

## Overview

Build an async Python CLI web crawler that accepts a base URL, crawls the site, and prints each page's URL along with all URLs found on that page. The crawler will only process URLs within the same domain.

## Architecture

### Project Structure

```
python/
├── pyproject.toml              # Project config, dependencies
├── README.md                   # Extended with design discussion
├── src/
│   └── crawler/
│       ├── __init__.py
│       ├── __main__.py         # CLI entry point
│       ├── cli.py              # Argument parsing
│       ├── crawler.py          # Main crawl orchestration
│       ├── fetcher.py          # Async HTTP client
│       ├── parser.py           # HTML parsing, link extraction
│       └── url_utils.py        # URL normalization, domain filtering
└── tests/
    ├── conftest.py             # Shared fixtures, test server
    ├── unit/
    │   ├── test_parser.py
    │   ├── test_url_utils.py
    │   └── test_fetcher.py
    └── integration/
        └── test_crawler.py
```

### Core Components

1. **CLI (`cli.py`)** - Parse command-line arguments using typer
   - Required: base URL
   - Optional: max concurrency, timeout, max depth, output format

2. **Crawler (`crawler.py`)** - Orchestrate the crawl
   - Manage URL frontier (queue of URLs to visit)
   - Track visited URLs (set)
   - Control concurrency with asyncio.Semaphore
   - Coordinate fetcher and parser

3. **Fetcher (`fetcher.py`)** - Async HTTP requests
   - Use httpx.AsyncClient with connection pooling
   - Handle timeouts, retries, error handling
   - Return response content and status

4. **Parser (`parser.py`)** - Extract links from HTML
   - Use BeautifulSoup with lxml parser
   - Extract href from <a> tags
   - Handle relative URLs, fragments, query params

5. **URL Utils (`url_utils.py`)** - URL handling
   - Normalise URLs (remove fragments, trailing slashes)
   - Check if URL belongs to same domain
   - Resolve relative URLs to absolute

## Implementation Phases

### ✅ Phase 1: Project Setup
- Update pyproject.toml with dependencies (httpx, beautifulsoup4, lxml, pytest, pytest-asyncio, pytest-httpserver)
- Create src/crawler package structure
- Set up pytest configuration

### ✅ Phase 2: URL Utilities
- Implement URL normalisation
- Implement domain extraction and comparison
- Implement relative URL resolution
- Write unit tests for URL utilities

### ✅ Phase 3: HTML Parser
- Implement link extraction from HTML
- Handle edge cases (malformed HTML, different encodings)
- Write unit tests with various HTML samples

### ✅ Phase 4: HTTP Fetcher
- Implement async fetcher with httpx
- Add configurable timeout and retry logic
- Handle common HTTP errors gracefully
- Write unit tests with mocked responses

### ✅ Phase 5: Crawler Core
- Implement crawl orchestration
- BFS traversal with concurrent fetching
- Visited URL tracking
- Output formatting (print page URL + found URLs)

### ✅ Phase 6: CLI Interface
- Implement argument parsing
- Wire up CLI to crawler
- Add helpful error messages and usage info

### ✅ Phase 7: Integration Tests
- Set up pytest-httpserver for local test server
- Create test site structure with multiple pages
- Test full crawl scenarios (depth, domain filtering, cycles)

## Key Design Decisions

1. **BFS vs DFS**: Use BFS (breadth-first) to ensure pages closer to root are crawled first

2. **Concurrency model**: asyncio with Semaphore to limit concurrent requests (default: 10)

3. **URL normalisation**: Strip fragments, normalise trailing slashes, lowercase domain

4. **Domain matching**: Same-domain only, normalise www (www.example.com = example.com)

5. **Error handling**: Log and continue on fetch errors, don't crash the crawl

6. **Output format**: Print as crawling happens (streaming output) vs batch at end

## Dependencies

```toml
dependencies = [
    "httpx>=0.27",
    "beautifulsoup4>=4.12",
    "lxml>=5.0",
    "typer>=0.12",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-httpserver>=1.0",
    "ruff>=0.5",
    "mypy>=1.10",
]
```

## CLI Interface

```bash
# Basic usage
uv run python -m crawler https://example.com

# With options
uv run python -m crawler https://example.com --max-concurrency 20 --timeout 30 --max-depth 5
```

## Output Format

```
Crawling: https://example.com
  Found URLs:
    - https://example.com/about
    - https://example.com/contact
    - https://example.com/products

Crawling: https://example.com/about
  Found URLs:
    - https://example.com/
    - https://example.com/team
    ...
```

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| pyproject.toml | Modify | Add dependencies, project config |
| src/crawler/__init__.py | Create | Package init |
| src/crawler/__main__.py | Create | Entry point |
| src/crawler/cli.py | Create | CLI argument parsing |
| src/crawler/crawler.py | Create | Main crawl logic |
| src/crawler/fetcher.py | Create | HTTP client |
| src/crawler/parser.py | Create | HTML parser |
| src/crawler/url_utils.py | Create | URL utilities |
| tests/conftest.py | Create | Test fixtures |
| tests/unit/test_*.py | Create | Unit tests |
| tests/integration/test_crawler.py | Create | Integration tests |
| README.md | Modify | Add design discussion |