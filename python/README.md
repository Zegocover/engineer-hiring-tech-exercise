# Zego Python Developer Test: Web Crawler

## Overview

This repository contains a Python-based web crawler. The crawler is designed to start from a given base URL, discover and process pages strictly within the same domain (excluding subdomains or external sites), and print each crawled page's URL along with the list of internal links found on it.

The implementation focuses on efficiency, maintainability, and scalability while adhering to the constraints: no use of heavy frameworks like Scrapy or Playwright, but leveraging standard libraries for HTTP requests (requests), HTML parsing (BeautifulSoup), and concurrency (concurrent.futures).

Key features:
- Command-line interface for easy execution.
- Concurrent fetching to boost speed without overwhelming resources.
- Robust URL normalization and domain filtering to ensure accuracy.
- Politeness features like rate limiting and error handling.
- Modular structure for testability and extensibility.

This solution was prioritizing a clean MVP first, followed by optimizations and testing.

## Setup and Requirements

### Prerequisites
- Python 3.8+
- Conda environment

### Installation
1. Clone the repository:
   ```
   git clone <repo-url>
   cd zego-crawler
   ```
2. Create and activate the Conda environment:
   ```
   conda env create -f environment.yml
   conda activate zego-crawler
   ```

### Running the Crawler
Run via the CLI:
```
python main.py <url> [--max-pages <int>] [--concurrency <int>] [--delay <float>]
```
- Example: `python main.py https://example.com --max-pages 100 --concurrency 10 --delay 1.0`

This will start crawling from the provided URL, printing each page and its internal links.

### Testing
Run unit tests:
```
pytest -v
```
Tests cover critical components: URL normalization, domain checking, link resolution, parsing, and fetching (with mocks).

## Design Decisions

### Overall Architecture
- **Modular Structure**: The code is organized into separate modules (`crawler.py`, `fetcher.py`, `parser.py`, `url_utils.py`, `cli.py`) to follow the Single Responsibility Principle (SRP). For example:
  - `url_utils.py` handles all URL-related logic (normalization, resolution, domain extraction) as pure functions, making them easy to test and reuse.
  - `fetcher.py` isolates HTTP requests and error handling.
  - `parser.py` focuses on HTML parsing and link extraction.
  - `crawler.py` orchestrates the crawl process.
  - `cli.py` manages argument parsing and entrypoint.

- **Crawling Algorithm**: Breadth-First Search (BFS) using a `collections.deque` for the queue (O(1) pops). Visited URLs are tracked in a set for O(1) lookups to prevent duplicates and cycles.

- **Concurrency Model**: Used `concurrent.futures.ThreadPoolExecutor` for parallel fetching in batches. This is ideal for I/O-bound tasks like HTTP requests, allowing multiple pages to be fetched simultaneously without blocking.
  
  Options considered: Sequential (simple but slow), multiprocessing (overkill for I/O, higher overhead), asyncio (more efficient for high concurrency but steeper learning curve and requires async-compatible libraries like aiohttp). Threading was chosen for simplicity and sufficient speed gains.

- **URL Handling**: 
  - Normalization removes fragments, trailing slashes (except root), and lowercases scheme/netloc to canonicalize URLs.
  - Domain filtering uses `urllib.parse.urlparse.netloc` for exact matches (e.g., "example.com" != "blog.example.com").
  - Resolution with `urljoin` handles relative, absolute, and protocol-relative links.

- **Error Handling**: 
  - Catches `requests.RequestException` and logs warnings/errors.
  - Configurable delay between requests to avoid server overload.
  - User-Agent header set to identify the crawler ethically.
  
  Options considered: Implementing robots.txt parsing (using `urllib.robotparser`) but omitted due to time; could be added easily.

- **Output and Logging**: Uses `print` for the required URL/links output (sorted for readability) and `logging` for info/warnings/errors. This separates user-facing output from debug info.

### Tools and Workflow
- **IDE**: Visual Studio Code with extensions for Python, Black (auto-formatting), and Flake8 (linting). This setup ensured PEP8 compliance and quick debugging.
- **AI Assistance**: 
  - GitHub Copilot was used for initial code suggestions (e.g., boilerplate for ThreadPoolExecutor and URL normalization). I reviewed and refined all suggestions to fit the design.
  - Grok (xAI) was consulted for brainstorming structure, trade-offs, and best practices (e.g., "efficient Python crawler without Scrapy"). No direct code copying; instead, it helped validate decisions like threading vs. asyncio.
  - StackOverflow and Python docs were referenced manually for specifics (e.g., `urljoin` behavior).
- **Version Control**: Git with commits reflecting incremental development.
- **Testing Framework**: Pytest with `responses` for mocking HTTP. Focused on unit tests for isolation; no end-to-end due to time.

## Trade-Offs

- **Speed vs. Resource Usage/Politeness**: Concurrency boosts speed but risks overwhelming servers or consuming high memory/CPU. Mitigated by batching, configurable workers (default 5), and delays (default 0.5s). Trade-off: Slower than max-parallel but ethical and stable.
  
- **Accuracy vs. Completeness**: Filters strictly to same domain and HTTP/HTTPS links, ignoring JS/mailto/anchors. This ensures accuracy but misses dynamic content (e.g., JS-loaded links). Trade-off: Simpler parsing (no browser emulation) vs. incomplete crawls; noted as a limitation since Playwright is forbidden.

- **Simplicity vs. Extensibility**: Kept code straightforward (no over-engineering like config files or DB persistence) to fit time box. Trade-off: Easier to understand/review but requires code changes for new features (e.g., multi-domain).

- **Testing Depth**: Unit tests cover 80%+ of critical paths but no integration tests for full crawls (time constraint). Trade-off: Quick validation vs. comprehensive coverage.

- **Performance on Large Sites**: Caps at `max_pages` (default 500) to prevent infinite runs. Trade-off: Safe but may truncate deep sites; could use max_depth instead.

## Extensions and Future Improvements

If not time-constrained, I would refine the following:

- **Multi-Domain Crawling**: Add a `--domains` flag accepting a comma-separated list or file. Modify `is_same_domain` to check against a set. For large-scale, switch CLI to a web API (e.g., Flask/FastAPI) with async endpoints for submitting jobs and polling results—better for monitoring long-running crawls than a blocking CLI.

- **Advanced Features**:
  - Respect `robots.txt` by integrating `urllib.robotparser` in `fetcher.py`.
  - Handle sitemaps.xml for faster discovery (parse and enqueue from it).
  - Persistence: Store visited/queue in Redis or SQLite for resumable/distributed crawls.
  - Output Formats: Add `--output json/csv` for structured exports.

- **Performance Optimizations**: 
  - Switch to asyncio + aiohttp for higher concurrency (100+ workers) without threading overhead.
  - Rate limiting with `ratelimit` library or token bucket for bursty but polite requests.

- **Monitoring and Metrics**: Integrate Prometheus or simple stats (e.g., crawl time, pages/sec) via logging.

- **Edge Cases**: More tests for redirects, non-UTF8 encodings, large pages. Add configurable timeouts/retries.

- **Deployment**: Dockerize for easy sharing; add CI/CD with GitHub Actions for tests/linting.