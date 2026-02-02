# Web Crawler Implementation Plan

## Summary of Requirements

- CLI app accepting a base URL
- Print each page URL and all URLs found on it
- Stay within the single domain (no subdomains)
- Maximize speed without sacrificing accuracy/resources
- **No Scrapy or Playwright** - can use HTTP/HTML libraries

---

## Architecture Options

| Approach | Pros | Cons |
|----------|------|------|
| **Async with aiohttp** (recommended) | Fast concurrent requests, efficient I/O, already in deps | Slightly more complex error handling |
| **Threading with requests** | Simpler mental model | GIL limits true parallelism, harder to scale |
| **Multiprocessing** | True parallelism | High memory overhead, complex IPC |

**Recommendation:** Async with `aiohttp` + `asyncio.Semaphore` for concurrency control. This is already scaffolded in the project.

---

## Core Components to Implement

### 1. URL Parser/Normalizer (`url_utils.py`)
- Normalize URLs (remove fragments, trailing slashes)
- Resolve relative URLs to absolute
- Extract and validate domain matching

### 2. Crawler Engine (`crawler.py`)
- Manage visited URL set
- Coordinate async workers
- Respect concurrency limits

### 3. HTML Parser (`parser.py`)
- Extract links from `<a href>` tags
- Handle malformed HTML gracefully

### 4. Output Formatter
- Print page URL and discovered links
- Consider structured output (JSON optional)

---

## Potential Problems & Mitigations

| Problem | Impact | Mitigation |
|---------|--------|------------|
| **Infinite loops** (cyclic links) | Hang/crash | Track visited URLs in a `set` |
| **URL normalization** (same page, different URLs) | Duplicate crawls | Canonicalize URLs (lowercase host, remove fragments, handle trailing `/`) |
| **Subdomain confusion** | Crawl wrong content | Strict domain check: `urllib.parse.urlparse(url).netloc == base_netloc` |
| **Rate limiting/blocking** | Errors, bans | Configurable delay, respect `robots.txt` (optional), User-Agent header |
| **Memory exhaustion** (large sites) | OOM | Limit max pages, use generators/streaming |
| **Timeouts/network errors** | Crash/hang | Per-request timeout, retry logic with backoff |
| **Non-HTML responses** | Parse errors | Check `Content-Type` header before parsing |
| **Relative URLs** | Missed links | Use `urljoin()` to resolve |
| **JavaScript-rendered content** | Missing links | Document as limitation (no JS support without Playwright) |
| **Encoding issues** | Garbled text | Handle charset detection |

---

## Proposed File Structure

```
src/crawler/
├── __init__.py
├── __main__.py          # CLI entry (exists)
├── crawler.py           # Main Crawler class
├── parser.py            # HTML parsing, link extraction
├── url_utils.py         # URL normalization, domain checking
└── models.py            # Optional: dataclasses for results

tests/
├── __init__.py
├── test_crawler.py
├── test_parser.py
├── test_url_utils.py
└── conftest.py          # Fixtures, mock server
```

---

## Testing Strategy

1. **Unit tests** - URL normalization, domain matching, link extraction
2. **Integration tests** - Mock HTTP responses with `aioresponses`
3. **Edge cases** - Circular links, malformed HTML, empty pages, non-HTML content

---

## Performance Considerations

- **Semaphore-bounded concurrency** - Prevent overwhelming the server
- **Connection pooling** - Reuse TCP connections via aiohttp session
- **Set for visited URLs** - O(1) lookup
- **lxml parser** - Faster than html.parser (already in deps)

---

## Extensions to Consider (if time permits)

1. **robots.txt respect** - Fetch and parse, skip disallowed paths
2. **Depth limiting** - `--max-depth` flag
3. **Output formats** - `--format json` for structured output
4. **Progress reporting** - Show pages crawled, queue size
5. **Sitemap support** - Parse sitemap.xml for faster discovery

---

## Design Decisions to Make

1. **Subdomain handling** - Strict same domain, or include `www.` variant?
2. **Output format** - Plain text, or add JSON option?
3. **Error handling** - Silent skip, log to stderr, or fail fast?
4. **Max pages limit** - Safety cap to prevent runaway crawls?

---

## Implementation Order

1. [ ] `url_utils.py` - URL normalization and domain checking
2. [ ] `parser.py` - HTML link extraction
3. [ ] `crawler.py` - Main async crawler engine
4. [ ] Update `__main__.py` - Wire everything together
5. [ ] Write unit tests for each module
6. [ ] Write integration tests with mocked responses
7. [ ] Add error handling and edge case coverage
8. [ ] Document design decisions in README
