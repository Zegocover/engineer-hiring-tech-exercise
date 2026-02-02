# Web Crawler Implementation Plan v2

## Evolution from v1
This version expands on the initial plan with deeper analysis of:
- Search strategy (BFS vs DFS)
- Concurrency patterns
- Speed optimizations

---

## Search Strategy Analysis

### Depth-First Search (DFS)
```
Start -> Page A -> Page A1 -> Page A1a -> (backtrack) -> Page A1b -> ...
```

| Aspect | Assessment |
|--------|------------|
| Parallelism | **Poor** - inherently sequential, follows one path at a time |
| Memory | Low - only stores current path stack |
| Predictability | Unpredictable - may get stuck in deep branches |
| Depth control | Harder to implement meaningful limits |
| Speed | **Slow** - cannot effectively batch concurrent requests |

### Breadth-First Search (BFS)
```
Start -> [Page A, Page B, Page C] -> [A1, A2, B1, B2, C1] -> ...
```

| Aspect | Assessment |
|--------|------------|
| Parallelism | **Excellent** - each level has N URLs to fetch concurrently |
| Memory | Higher - queue grows with site width |
| Predictability | Predictable - explores systematically by distance |
| Depth control | Natural `--max-depth` implementation |
| Speed | **Fast** - perfect fit for async worker pools |

### Decision: BFS with Async Workers

**Rationale:**
1. Can dispatch 10-50 concurrent requests from the queue
2. Important pages (nav, main content) are typically shallow
3. Natural fit for `asyncio.Queue` + semaphore pattern
4. Easy to implement depth limiting for large sites

---

## Concurrency Architecture

### Option A: Simple Semaphore (Chosen)
```python
async def crawl():
    semaphore = asyncio.Semaphore(max_concurrent)
    queue = asyncio.Queue()

    async def worker():
        while True:
            url, depth = await queue.get()
            async with semaphore:
                links = await fetch_and_parse(url)
                for link in links:
                    if link not in visited:
                        await queue.put((link, depth + 1))
            queue.task_done()

    # Start N workers
    workers = [asyncio.create_task(worker()) for _ in range(num_workers)]
    await queue.join()
```

**Pros:** Simple, effective, easy to reason about
**Cons:** Workers may idle if queue is temporarily empty

### Option B: Producer-Consumer with Backpressure
More complex - separate fetcher and parser tasks with bounded queues.

**Verdict:** Option A is sufficient for this task. Option B adds complexity without significant benefit for single-domain crawling.

---

## Speed Optimizations

### 1. Connection Pooling (Critical)
```python
connector = aiohttp.TCPConnector(
    limit=100,           # Total connections
    limit_per_host=20,   # Per-host limit
    ttl_dns_cache=300,   # Cache DNS lookups
    keepalive_timeout=30 # Reuse connections
)
session = aiohttp.ClientSession(connector=connector)
```

### 2. Response Streaming (Important)
Don't download entire response before checking content type:
```python
async with session.get(url) as response:
    content_type = response.headers.get('Content-Type', '')
    if 'text/html' not in content_type:
        return []  # Skip non-HTML early
    html = await response.text()
```

### 3. Parser Selection (Moderate)
| Parser | Speed | Robustness |
|--------|-------|------------|
| `lxml` | **Fastest** | Good |
| `html.parser` | Slow | Built-in |
| `html5lib` | Slowest | Best for broken HTML |

**Decision:** Use `lxml` (already in dependencies)

### 4. URL Deduplication (Critical)
```python
# Use set for O(1) lookup
visited: set[str] = set()

# Normalize before checking
normalized = normalize_url(url)
if normalized in visited:
    continue
visited.add(normalized)
```

### 5. Early Termination Checks
Skip URLs before fetching:
- Already visited
- Non-HTTP scheme (mailto:, javascript:, tel:)
- Different domain
- File extensions (.pdf, .jpg, .zip, etc.)

---

## Revised Component Design

### url_utils.py
```python
def normalize_url(url: str) -> str:
    """Canonicalize URL for deduplication."""
    # - Lowercase scheme and host
    # - Remove fragments (#section)
    # - Remove trailing slash (except root)
    # - Sort query parameters (optional)

def is_same_domain(url: str, base_domain: str) -> bool:
    """Check if URL belongs to the target domain."""
    # Strict match: example.com only
    # NOT www.example.com or sub.example.com

def should_skip_url(url: str) -> bool:
    """Filter out non-crawlable URLs."""
    # - Non-HTTP schemes
    # - Binary file extensions
    # - Data URIs
```

### parser.py
```python
def extract_links(html: str, base_url: str) -> list[str]:
    """Extract and resolve all <a href> links."""
    # - Parse with lxml
    # - Find all anchor tags
    # - Resolve relative URLs with urljoin
    # - Return absolute URLs only
```

### crawler.py
```python
class Crawler:
    def __init__(self, base_url: str, concurrency: int, timeout: int):
        self.base_url = base_url
        self.base_domain = extract_domain(base_url)
        self.concurrency = concurrency
        self.timeout = timeout
        self.visited: set[str] = set()

    async def crawl(self) -> None:
        """BFS crawl with async workers."""
        # 1. Create session with connection pooling
        # 2. Initialize queue with base_url
        # 3. Spawn worker tasks
        # 4. Wait for queue to drain
        # 5. Print results as we go
```

---

## Output Format

### Default: Streaming Plain Text
```
[Page] https://example.com/
  -> https://example.com/about
  -> https://example.com/contact
  -> https://example.com/products

[Page] https://example.com/about
  -> https://example.com/
  -> https://example.com/team
```

**Rationale:**
- Print as we crawl (streaming) - shows progress
- Human readable for manual inspection
- Easy to grep/filter

### Optional: JSON (future extension)
```json
{"page": "https://example.com/", "links": ["...", "..."]}
```

---

## Error Handling Strategy

| Error Type | Action |
|------------|--------|
| Connection timeout | Log warning, skip page, continue |
| HTTP 4xx | Log, skip (page doesn't exist or forbidden) |
| HTTP 5xx | Retry once, then skip |
| Parse error | Log warning, return empty links |
| Invalid URL | Skip silently (filter in url_utils) |

**Principle:** Never crash. Log errors to stderr, continue crawling.

---

## Implementation Order (Revised)

1. [ ] `url_utils.py` - URL normalization, domain checking, filtering
2. [ ] Unit tests for url_utils
3. [ ] `parser.py` - Link extraction with lxml
4. [ ] Unit tests for parser
5. [ ] `crawler.py` - BFS async crawler with connection pooling
6. [ ] Integration tests with aioresponses mocks
7. [ ] Wire up `__main__.py`
8. [ ] End-to-end testing against real sites
9. [ ] Error handling and edge cases
10. [ ] Documentation and README updates

---

## Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Search strategy | BFS | Best for concurrent fetching |
| Concurrency model | Async + Semaphore | Simple and effective |
| HTTP client | aiohttp | Async, connection pooling |
| HTML parser | lxml | Fastest option |
| Subdomain handling | Strict same-domain | Per requirements |
| Output format | Streaming plain text | Shows progress, human readable |
| Error handling | Log and continue | Resilient crawling |

---

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Site blocks crawler | Medium | Set proper User-Agent, respect rate limits |
| Memory issues on large sites | Low | Add `--max-pages` limit |
| Slow sites timeout | Medium | Configurable timeout, retry logic |
| Malformed HTML | High | lxml handles most cases, wrap in try/except |
