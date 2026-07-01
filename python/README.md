# python-developer-test

# Zego

## About Us

At Zego, we understand that traditional motor insurance holds good drivers back.
It's too complicated, too expensive, and it doesn't reflect how well you actually drive.
Since 2016, we have been on a mission to change that by offering the lowest priced insurance for good drivers.

From van drivers and gig economy workers to everyday car drivers, our customers are the driving force behind everything we do. We've sold tens of millions of policies and raised over $200 million in funding. And we’re only just getting started.

## Our Values

Zego is thoroughly committed to our values, which are the essence of our culture. Our values defined everything we do and how we do it.
They are the foundation of our company and the guiding principles for our employees. Our values are:

<table>
    <tr><td><img src="../doc/assets/blaze_a_trail.png?raw=true" alt="Blaze a trail" width=50></td><td><b>Blaze a trail</b></td><td>Emphasize curiosity and creativity to disrupt the industry through experimentation and evolution.</td></tr>
    <tr><td><img src="../doc/assets/drive_to_win.png?raw=true" alt="Drive to win" width=50></td><td><b>Drive to win</b></td><td>Strive for excellence by working smart, maintaining well-being, and fostering a safe, productive environment.</td></tr>
    <tr><td><img src="../doc/assets/take_the_wheel.png?raw=true" alt="Take the wheel" width=50></td><td><b>Take the wheel</b></td><td>Encourage ownership and trust, empowering individuals to fulfil commitments and prioritize customers.</td></tr>
    <tr><td><img src="../doc/assets/zego_before_ego.png?raw=true" alt="Zego before ego" width=50></td><td><b>Zego before ego</b></td><td>Promote unity by working as one team, celebrating diversity, and appreciating each individual's uniqueness.</td></tr>
</table>

## The Engineering Team

Zego puts technology first in its mission to define the future of the insurance industry.
By focusing on our customers' needs we're building the flexible and sustainable insurance products
and services that they deserve. And we do that by empowering a diverse, resourceful, and creative
team of engineers that thrive on challenge and innovation.

### How We Work

- **Collaboration & Knowledge Sharing** - Engineers at Zego work closely with cross-functional teams to gather requirements,
  deliver well-structured solutions, and contribute to code reviews to ensure high-quality output.
- **Problem Solving & Innovation** - We encourage analytical thinking and a proactive approach to tackling complex
  problems. Engineers are expected to contribute to discussions around optimization, scalability, and performance.
- **Continuous Learning & Growth** - At Zego, we provide engineers with abundant opportunities to learn, experiment and
  advance. We positively encourage the use of AI in our solutions as well as harnessing AI-powered tools to automate
  workflows, boost productivity and accelerate innovation. You'll have our full support to refine your skills, stay
  ahead of best practices and explore the latest technologies that drive our products and services forward.
- **Ownership & Accountability** - Our team members take ownership of their work, ensuring that solutions are reliable,
  scalable, and aligned with business needs. We trust our engineers to take initiative and drive meaningful progress.

## Who should be taking this test?

This test has been created for all levels of developer, Junior through to Staff Engineer and everyone in between.
Ideally you have hands-on experience developing Python solutions using Object Oriented Programming methodologies in a commercial setting. You have good problem-solving abilities, a passion for writing clean and generally produce efficient, maintainable scaleable code.

## The test 🧪

Create a Python app that can be run from the command line that will accept a base URL to crawl the site.
For each page it finds, the script will print the URL of the page and all the URLs it finds on that page.
The crawler will only process that single domain and not crawl URLs pointing to other domains or subdomains.
Please employ patterns that will allow your crawler to run as quickly as possible, making full use any
patterns that might boost the speed of the task, whilst not sacrificing accuracy and compute resources.
Do not use tools like Scrapy or Playwright. You may use libraries for other purposes such as making HTTP requests, parsing HTML and other similar tasks.

## The objective

This exercise is intended to allow you to demonstrate how you design software and write good quality code.
We will look at how you have structured your code and how you test it. We want to understand how you have gone about
solving this problem, what tools you used to become familiar with the subject matter and what tools you used to
produce the code and verify your work. Please include detailed information about your IDE, the use of any
interactive AI (such as Copilot) as well as any other AI tools that form part of your workflow.

You might also consider how you would extend your code to handle more complex scenarios, such a crawling
multiple domains at once, thinking about how a command line interface might not be best suited for this purpose
and what alternatives might be more suitable. Also, feel free to set the repo up as you would a production project.

Extend this README to include a detailed discussion about your design decisions, the options you considered and
the trade-offs you made during the development process, and aspects you might have addressed or refined if not constrained by time.

# Instructions

1. Create a repo.
2. Tackle the test.
3. Push the code back.
4. Add us (@nktori, @danyal-zego, @bogdangoie, @cypherlou, @marliechiller and @ZEGODiogoAlves) as collaborators and tag us to review.
5. Notify your TA so they can chase the reviewers.


# Exercise Resolution

## Overview

Development of a single-domain async web crawler built in Python. It accepts a URL via the command line, crawls all pages within that exact domain, capable of printing the URL of each page along with all links discovered on it.

---

## Development Environment & Tools

- **IDE**: VS Code with Python extension, Pylance for type checking
- **AI Assistance**: GitHub Copilot (used for autocomplete suggestions, rubber-ducking design decisions, and generating test scaffolding)
- **Python version**: 3.11+ (for modern type syntax: `X | Y` unions, `set[str]`)
- **Package management**: pip with pyproject.toml
- **Linting**: Ruff (fast, covers flake8/isort/pyupgrade rules)
- **Type checking**: mypy in strict mode
- **Testing**: pytest with pytest-asyncio and aioresponses for HTTP mocking

---

## Architecture & Design Decisions

### High-Level Design

The crawler follows a **producer-consumer pattern** with a bounded worker pool:

```
┌─────────────────────────────────────────────────────┐
│                    CLI (cli.py)                       │
│  Parses args, validates URL, sets up logging         │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│               Crawler (crawler.py)                    │
│  Orchestrates workers, manages queue & visited set   │
│                                                      │
│  ┌──────────┐  ┌──────────┐       ┌──────────┐     │
│  │ Worker 1 │  │ Worker 2 │  ...  │ Worker N │     │
│  └────┬─────┘  └────┬─────┘       └────┬─────┘     │
│       │              │                  │           │
│       ▼              ▼                  ▼           │
│  ┌──────────────────────────────────────────┐       │
│  │          asyncio.Queue (URL frontier)     │       │
│  └──────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│               Parser (parser.py)                     │
│  Extracts & normalises links from HTML               │
└─────────────────────────────────────────────────────┘
```

### Why Async (asyncio + aiohttp)?

Web crawling is heavily I/O-bound — the dominant cost is waiting for HTTP responses. An async approach with `aiohttp` allows us to have many requests in flight simultaneously on a single thread, without the overhead of OS threads or processes. This gives:

- **High concurrency** without thread-safety complexity
- **Low memory overhead** compared to thread pools
- **Cooperative scheduling** — no GIL contention issues

**Alternatives considered:**
- `threading` + `requests`: Simpler mental model, but limited by GIL overhead and thread creation costs at high concurrency
- `multiprocessing`: Better for CPU-bound work; overkill for I/O waiting
- `trio`/`anyio`: More opinionated async frameworks; `asyncio` is stdlib and sufficient

### Concurrency Control

The crawler uses an `asyncio.Semaphore` to bound the number of concurrent HTTP requests. This prevents:
- Overwhelming the target server (polite crawling)
- Exhausting local system resources (file descriptors, memory)
- Getting rate-limited or blocked

The default of 10 concurrent requests is a balanced starting point that can be tuned via CLI.

### URL Normalisation

Consistent URL normalisation prevents duplicate crawling of the same resource:
- Lowercase scheme and host
- Strip fragments (`#section`)
- Remove trailing slashes (except root `/`)
- Preserve query strings and ports

This is critical for correctness — without it, the crawler would visit the same page multiple times under different string representations.

### Domain Filtering

One requirement specifies **same domain only, no subdomains**. For that, the implementation compares the full `netloc` (host + port) exactly:
- `example.com` ✓
- `www.example.com` ✗ (different netloc)
- `sub.example.com` ✗ (different netloc)
- `example.com:8080` ✗ (different port)

This is a deliberate strict interpretation. A looser alternative (e.g., matching the registered domain) would require a library like `tldextract` and would make the crawl scope less precise, because it raises extra policy questions such as whether `www.example.com`, `blog.example.com`, or different ports should count as the "same domain".

### Separation of Concerns

The code is split into three focused modules:

1. **`parser.py`** — Pure functions for URL manipulation and HTML parsing. No I/O and no state. This allows to test in isolation.
2. **`crawler.py`** — Async orchestration logic. Manages the work queue, worker pool, and visited-URL tracking.
3. **`cli.py`** — User interface layer. Argument parsing, output formatting, entry point.

This separation means:
- The parser can be reused independently
- The crawler can be driven programmatically (not just from CLI)
- The CLI can be swapped for an API without touching core logic

### Error Handling Strategy

The crawler is designed to be **resilient** — a single page failure should not halt the entire crawl:
- Timeouts, connection errors, and non-HTML responses are recorded in the `PageResult` but don't stop other workers
- Each error is logged and reported in the output
- The exit code reflects whether all pages were successful

### Output Design

The CLI prints results incrementally as each page completes (via the `on_page_crawled` callback). This gives users immediate feedback during long crawls rather than waiting for everything to finish. A final summary provides aggregate statistics.

---

## Trade-offs & Limitations

### What I prioritised
- **Correctness**: Thorough URL normalisation, strict domain matching, deduplication
- **Speed**: Async I/O, connection pooling, DNS caching, bounded concurrency
- **Testability**: Pure functions, dependency injection (callback), HTTP mocking
- **Readability**: Clear module boundaries, type annotations, docstrings

### What I de-prioritised (given time constraints)
- **robots.txt compliance**: The `respect_robots` parameter exists as a placeholder but is not implemented. A production crawler should parse and honour robots.txt
- **Rate limiting**: Beyond concurrency bounds, there's no per-host delay. A polite crawler would add configurable delays
- **Retry logic**: Failed requests are not retried. A production version would use exponential backoff
- **Depth limiting**: No maximum crawl depth is enforced. Large sites could be crawled indefinitely
- **URL deduplication heuristics**: Query parameter ordering, www/non-www equivalence, etc.
- **Content caching**: No ETag/Last-Modified handling for already-seen content

---

## Performance Characteristics

| Technique | Benefit |
|-----------|---------|
| `asyncio` event loop | Single-thread, no context-switch overhead |
| `aiohttp.TCPConnector` with connection pooling | Reuses TCP connections |
| DNS cache (`ttl_dns_cache=300`) | Avoids repeated DNS lookups |
| `lxml` parser (via BeautifulSoup) | C-based HTML parsing, ~5x faster than html.parser |
| Semaphore-bounded concurrency | Prevents resource exhaustion |
| Set-based URL tracking | O(1) deduplication lookups |
| Incremental output | No memory accumulation for display |

---

## Extending the Crawler

- **Support multiple starting domains**: accept more than one seed URL and run one crawler instance per domain, while keeping separate visited sets and shared concurrency limits.
- **Move beyond a CLI-only interface**: expose crawling as an API or background job so runs can be triggered, monitored, and consumed by other systems.
- **Persist results and crawl history**: store discovered pages, links, and previous runs instead of printing everything only to stdout.
- **Add basic politeness controls**: support `robots.txt`, respect crawl delays, and apply per-host rate limiting to avoid overloading target sites.

---

## Testing Strategy

Tests are organised by module:

- **`test_parser.py`**: Unit tests for pure URL functions — normalisation, domain checks, link extraction from various HTML structures
- **`test_crawler.py`**: Integration tests using `aioresponses` to mock HTTP responses — verifies crawling behaviour, deduplication, error handling, and callbacks
- **`test_cli.py`**: Tests for argument validation and URL normalisation at the CLI boundary

The testing approach prioritises:
- **Determinism**: Mocked HTTP means tests never hit real servers
- **Speed**: No real I/O, tests run in milliseconds
- **Coverage of edge cases**: Empty pages, non-HTML, timeouts, cycles, whitespace in URLs

---

## How to Run

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install runtime dependencies only
make install
# Or install development dependencies as well
make dev

# Run the crawler
crawl https://example.com
crawl https://example.com --concurrency 20 --timeout 60 --verbose
# Or via Python module
python -m crawler https://example.com

# Run tests
make test

# Run linting
make lint

# Type checking
make type-check
```

---

## Project Structure

```
.
├── pyproject.toml              # Project metadata, dependencies, and tool config
├── Makefile                    # Development commands
├── .gitignore
├── README
├── src/
│   ├── crawler/
│   │   ├── __init__.py         # Package marker
│   │   ├── __main__.py         # `python -m crawler` support
│   │   ├── cli.py              # CLI argument parsing and output formatting
│   │   ├── crawler.py          # Async crawler core
│   │   └── parser.py           # URL normalisation and HTML link extraction
│   └── web_crawler.egg-info/   # Packaging metadata generated by editable install
└── tests/
    ├── __init__.py
    ├── conftest.py             # Shared test fixtures
    ├── test_cli.py             # CLI validation tests
    ├── test_crawler.py         # Crawler behaviour tests
    └── test_parser.py          # Parser and URL handling tests
```
