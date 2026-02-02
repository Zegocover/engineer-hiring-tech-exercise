# Code Review Log

This document tracks review checkpoints during implementation.

---

## Review 1: url_utils.py

**Date:** 2026-02-01
**Status:** Approved

### Files Created
- `src/crawler/url_utils.py` - URL utilities module
- `tests/test_url_utils.py` - 32 unit tests

### Functions Implemented

| Function | Purpose |
|----------|---------|
| `extract_domain(url)` | Get lowercase domain from URL |
| `normalize_url(url, base_url)` | Canonicalize URL (remove fragments, trailing slashes, resolve relative) |
| `is_same_domain(url, base_domain)` | Strict domain matching |
| `should_skip_url(url)` | Filter non-crawlable URLs (mailto, .pdf, etc.) |
| `is_valid_http_url(url)` | Validate HTTP/HTTPS URLs |

### Test Results
```
32 passed in 0.03s
```

### Design Decisions
- Strict domain matching (www.example.com ≠ example.com) per requirements
- Comprehensive skip list for binary files and non-HTTP schemes
- Path case preserved (only scheme/host lowercased)
- Uses only stdlib (`urllib.parse`) - no external dependencies

### Notes
- All edge cases covered (empty URLs, ports, case sensitivity, subdomains)
- Ready for integration with parser and crawler modules

---

## Review 2: parser.py

**Date:** 2026-02-01
**Status:** Approved

### Files Created
- `src/crawler/parser.py` - HTML parsing module
- `tests/test_parser.py` - 27 unit tests

### Functions Implemented

| Function | Purpose |
|----------|---------|
| `extract_links(html, base_url)` | Extract and normalize all links from HTML |
| `is_html_content_type(content_type)` | Check if Content-Type indicates HTML |

### Test Results
```
27 passed in 0.15s
```

### Design Decisions
- Uses BeautifulSoup with lxml parser (fastest option)
- Deduplicates links within the same page
- Integrates with url_utils for normalization and filtering
- External links are extracted (filtering happens in crawler)
- Gracefully handles malformed HTML

### Edge Cases Covered
- Empty/whitespace hrefs
- Anchors without href attribute
- Malformed HTML
- All skip conditions (mailto, javascript, binary files)

---

## Review 3: crawler.py

**Date:** 2026-02-01
**Status:** Approved

### Files Created
- `src/crawler/crawler.py` - Async BFS crawler engine
- `tests/test_crawler.py` - 16 integration tests

### Classes/Functions Implemented

| Component | Purpose |
|-----------|---------|
| `CrawlResult` | Dataclass for page crawl results |
| `CrawlerConfig` | Configuration (concurrency, timeout, max_pages) |
| `Crawler` | Main async crawler with BFS traversal |

### Test Results
```
76 passed in 0.24s (all tests)
```

### Design Decisions
- BFS traversal with asyncio.Queue for concurrent processing
- Semaphore-bounded concurrency (prevents overwhelming servers)
- aiohttp with connection pooling and DNS caching
- Callback support for streaming output
- Graceful error handling (logs and continues)

### Bug Fix During Review
- Fixed URL normalization: empty path now normalized to `/`
- Added test case: `test_adds_root_slash_when_missing`
- This prevented duplicate crawling of root URL

### Key Features
- External domains filtered (not followed)
- Subdomains treated as separate domains
- Non-HTML content skipped early (checks Content-Type)
- HTTP errors logged but don't stop crawl
- Configurable max_pages limit

---

## Review 4: __main__.py (CLI Integration)

**Date:** 2026-02-01
**Status:** Approved

### Files Modified
- `src/crawler/__main__.py` - Complete CLI implementation

### Features Implemented

| Feature | Description |
|---------|-------------|
| URL validation | Rejects non-HTTP URLs with helpful error |
| Streaming output | Prints pages as they're crawled (callback) |
| Quiet mode | `-q` flag for machine-parseable output |
| Verbose mode | `-v` flag for debug logging |
| Max pages limit | `-m` flag to cap crawl size |
| Summary stats | Pages crawled, links found, errors |
| Keyboard interrupt | Graceful Ctrl+C handling |

### CLI Arguments
```
crawl [-h] [-c CONCURRENCY] [-t TIMEOUT] [-m MAX_PAGES] [-v] [-q] url
```

### Code Quality
- All 76 tests passing
- mypy: no type errors
- ruff: all checks passed

### Fixes During Review
- Fixed BeautifulSoup type handling in parser.py
- Updated imports per ruff (Callable from collections.abc)
- Removed unused pytest imports

---

## Review 5: README Documentation

**Date:** 2026-02-01
**Status:** Approved

### Files Modified
- `README.md` - Added comprehensive design documentation

### Sections Added

| Section | Content |
|---------|---------|
| Quick Start | Installation and usage instructions |
| CLI Usage | Complete argument documentation |
| Architecture Overview | Module structure diagram |
| Key Design Decisions | BFS, async, URL normalization, domain matching |
| Trade-offs Made | Simplicity vs robustness, memory vs speed |
| Future Improvements | Prioritized list of enhancements |
| Tools Used | IDE, AI assistant, dependencies |
| Multiple Domain Extension | Architecture discussion |

### Documentation Quality
- Includes decision rationale with alternatives considered
- Trade-off analysis shows engineering judgment
- Clear upgrade path for production use

---

## Final Summary

**Implementation Complete**

| Metric | Value |
|--------|-------|
| Total tests | 76 |
| Test pass rate | 100% |
| Type errors | 0 |
| Lint errors | 0 |
| Modules | 4 |
| Lines of code | ~500 |

**All requirements met:**
- CLI accepts base URL
- Prints page URL and discovered links
- Single domain only (subdomains excluded)
- Fast async execution with concurrency control
- No Scrapy or Playwright
