# Web Crawler

A concurrent web crawler written in Go. Given a base URL, it crawls all pages within that domain and prints discovered URLs. It respects robots.txt, handles rate limiting, and can optionally use Redis for distributed crawling.

## Requirements

- Go 1.21+
- Redis (optional, for distributed mode)

## Usage

```bash
# Build
go build -o crawler ./cmd/crawler

# Basic usage
./crawler -url https://example.com

# With options
./crawler -url https://books.toscrape.com -workers 5 -rate 2 -max-urls 100

# Run directly without building
go run ./cmd/crawler -url https://example.com -max-urls 10
```

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `-url` | (required) | Base URL to crawl |
| `-workers` | 10 | Number of concurrent workers |
| `-rate` | 5.0 | Requests per second |
| `-max-urls` | 0 | Maximum URLs to crawl (0 = unlimited) |
| `-redis` | false | Enable Redis for distributed mode |
| `-redis-addr` | localhost:6379 | Redis server address |
| `-user-agent` | GoCrawler/1.0 | User agent string |

## Running with Docker

```bash
# Single instance
docker build -t crawler .
docker run crawler -url https://example.com -max-urls 10

# Distributed mode with Redis
docker-compose up
```

## Running Tests

```bash
go test ./...
```

## Project Structure

```
├── cmd/crawler/          # CLI entrypoint
├── internal/
│   ├── crawler/          # Main crawler orchestration
│   ├── fetcher/          # HTTP client with rate limiting
│   ├── parser/           # HTML link extraction
│   ├── frontier/         # URL queue (memory + Redis implementations)
│   ├── dedup/            # URL deduplication using bloom filter
│   ├── robots/           # robots.txt parsing and compliance
│   └── domain/           # URL normalization utilities
├── Dockerfile
└── docker-compose.yml
```

## Design Decisions

### Why Go instead of Python?

The task mentioned Python, but I went with Go for a few reasons:

1. Goroutines make concurrent crawling straightforward. Python's asyncio works but Go's concurrency model felt more natural for this use case.
2. I've been writing more Go lately and wanted to use something I'm comfortable with.
3. Single binary deployment is nice for CLI tools.

If Python was a hard requirement, I would have used `aiohttp` with `asyncio` for concurrent requests and `BeautifulSoup` or `lxml` for parsing.

### Concurrency Model

The crawler uses a worker pool pattern. A configurable number of workers pull URLs from a shared frontier (queue) and process them concurrently. Each worker:

1. Pops a URL from the frontier
2. Checks robots.txt rules
3. Fetches the page (respecting rate limits)
4. Extracts links
5. Pushes new same-domain URLs back to the frontier

I considered a few alternatives:

- **Unbounded goroutines**: Spawn a goroutine per URL. Simple but can explode memory and hammer the target server. Ruled out.
- **Channel-based pipeline**: More complex, didn't feel necessary for this scope.
- **Worker pool**: Good balance of control and simplicity. Went with this.

### Rate Limiting

Uses `golang.org/x/time/rate` for token bucket rate limiting. The limiter is shared across all workers, so `-rate 5` means 5 requests per second total, not per worker.

I also check for `Crawl-delay` in robots.txt and adjust the rate accordingly. If the site specifies a crawl delay, we respect it even if it's slower than what the user requested.

### URL Deduplication

Bloom filter using `bits-and-blooms/bloom`. Trade-off here is memory vs accuracy:

- Hash set: 100% accurate but memory grows with crawl size
- Bloom filter: Fixed memory, small false positive rate (might skip a URL we haven't seen)

For most crawls, the bloom filter's false positive rate (configured at 0.01%) is acceptable. A production system might use a hybrid approach or persistent storage.

### Frontier (URL Queue)

Two implementations:

1. **Memory**: Simple thread-safe queue. Good for single-instance crawls.
2. **Redis**: Enables multiple crawler instances to share work. Uses Redis lists with blocking pop.

The interface is simple enough that adding other backends (PostgreSQL, RabbitMQ, etc.) would be straightforward.

### robots.txt

Fetched once at crawl start and cached. Uses the `temoto/robotstxt` library. We check both `Disallow` rules and `Crawl-delay`. If robots.txt can't be fetched, we proceed with crawling (fail-open) but log a warning.

### Link Extraction

Uses `goquery` (Go port of jQuery) for HTML parsing. Extracts `href` from anchor tags, resolves relative URLs against the page base, and normalizes them (removes fragments, trailing slashes).

Only follows links to the same domain. "Same domain" means exact host match - `www.example.com` and `example.com` are treated as different domains. This is conservative but avoids accidentally crawling more than intended.

## Trade-offs and Shortcuts

Things I'd do differently with more time:

### No persistent state

If the crawler crashes, it starts over. A production crawler would checkpoint progress to disk or a database. Could serialize the frontier and bloom filter periodically. I could have used a Bloom filter or a hash set in Redis, but that would have added latency, so there’s a trade-off there.

### Basic error handling

Failed requests are logged and skipped. No retry logic, no exponential backoff. A real crawler would have configurable retry policies, maybe a dead-letter queue for URLs that consistently fail.

### No depth limiting

Currently crawls everything reachable. Adding a `-max-depth` flag would be useful for limiting how far from the seed URL we go.

### Single-host rate limiting

Rate limit is global. If crawling multiple domains (which we don't currently support), each domain should have its own rate limiter. The current design assumes single-domain crawls.

### No content storage

We just print URLs. A real crawler would store page content, extract structured data, index for search, etc. The `Result` struct has the response body, so extending this would be straightforward.

### Limited URL normalization

We handle basics (fragments, trailing slashes) but not everything (query param ordering, case normalization, etc.). Could use a dedicated URL canonicalization library.

## Extending to Multiple Domains

The task asked about crawling multiple domains. Current design doesn't support this well because:

1. Single rate limiter (should be per-domain)
2. Single robots.txt cache (should be per-domain)
3. CLI takes one URL

To support multiple domains properly:

1. Introduce a `Domain` struct holding domain-specific state (rate limiter, robots.txt, bloom filter)
2. Shard workers by domain or use a domain-aware scheduler
3. Consider politeness - don't hammer one domain while others are idle

At that point, a CLI becomes awkward. You'd want:

- Config file (YAML/JSON) listing seed URLs and per-domain settings
- REST API for submitting crawl jobs and checking status
- Web UI for monitoring
- Message queue for distributing work across machines

Basically, you'd be building a crawl orchestration system rather than a CLI tool.

## Development Environment

- **Editor**: Cursor (VS Code fork with AI features)
- **Terminal**: Claude Code for quick iterations and when I'm away from the IDE
- **Testing**: `go test` with table-driven tests. Mock fetcher for unit tests. Manual testing against `books.toscrape.com`.
- **OS**: macOS

## AI in My Workflow

Since the task asked about AI tools, here's an honest breakdown.

I used **Cursor** and **Claude Code** throughout this project. At this point they're just part of how I write code, like how an IDE's autocomplete or a linter is - I don't really think about it as "using AI" anymore, it's just... typing.

What AI helped with:
- **Boilerplate**: Interface definitions, struct scaffolding, the repetitive parts of test tables. The stuff I know how to write but is tedious.
- **Rubber ducking**: "Here's my approach for X, does this make sense?" - sometimes it catches things, sometimes it confirms I'm on track.
- **Test edge cases**: "What inputs might break this function?" is a great prompt. Caught a few nil pointer cases I would've missed.
- **Documentation**: First drafts of comments and this README. I edited heavily, but starting from something is faster than starting from nothing.

What I did myself:
- **Architecture decisions**: The worker pool vs channels debate, choosing bloom filter over hash set, the frontier interface design - that's all me staring at the ceiling thinking.
- **Debugging the tricky stuff**: When the crawler was double-counting URLs or workers were deadlocking, I had to actually understand the code to fix it. AI can suggest, but concurrent bugs need a human brain (and a lot of print statements).
- **Knowing what to build**: AI is good at "how" but I had to figure out "what". The decision to support Redis, to respect robots.txt crawl-delay, to use token bucket rate limiting - those came from experience with similar systems.

My honest take: AI makes me faster at the mechanical parts, which leaves more time for the interesting parts. It's like having a junior dev who types really fast and never gets tired, but you still have to review their PRs carefully.

## JavaScript-Rendered Pages

The current implementation only fetches raw HTML, so it won't see content rendered by JavaScript (React, Vue, etc.). For SPAs, you need to actually execute the JavaScript.

**Options I considered:**

1. **Headless browser (Playwright, Puppeteer, Rod)** - Most reliable. The browser renders the page fully, you get the final DOM. Downside is resource usage (~150-200MB per browser instance) and slower crawls. For Go, `rod` or `chromedp` are the common choices.

2. **Hybrid approach** - First fetch with plain HTTP. If the response looks like a JS shell (small HTML with big script bundles, or specific framework markers), then re-fetch with a headless browser. This avoids the browser overhead for static pages.

3. **Prerendering services** - Third-party APIs like Prerender.io or Rendertron. You offload the rendering entirely. Adds latency and cost, but zero infrastructure on your end.

If I were adding JS support, I'd probably go with a hybrid approach: plain HTTP first, detect if JS rendering is needed (check for empty body, known SPA patterns like `<div id="root"></div>` with no content), and only then spin up a browser. Could also maintain a per-domain cache of "needs JS" so we don't have to detect every time.

The browser pool would need careful management - browsers are heavy, so you'd want a small pool (maybe 2-3 instances) separate from the regular HTTP workers, with its own queue for JS-heavy URLs.

## What I'd Add Next

If I were to keep working on this:

1. **Retry logic** with exponential backoff
2. **Crawl state persistence** for resumable crawls
3. **Prometheus metrics** for monitoring (URLs/sec, queue depth, error rates)
4. **Content-Type filtering** to skip non-HTML early
5. **Sitemap.xml support** for discovering URLs
6. **More comprehensive URL normalization**
7. **JavaScript rendering** for SPAs (hybrid approach with headless browser fallback)
