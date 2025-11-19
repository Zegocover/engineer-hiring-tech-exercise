# Zego Crawler (Java)

This project provides a lightweight, high-performance web crawler implemented in Java. The application accepts a base URL from the command line and performs a structured crawl of all pages within the same domain. For each page visited, the crawler prints the page’s URL followed by all hyperlinks discovered on that page.

The crawler is designed with simplicity, efficiency, and correctness in mind. It uses Java’s modern HttpClient for fast, asynchronous-friendly network operations, a fixed-size worker pool for concurrent fetching, and a thread-safe queue and URL tracking system to ensure that each page is processed at most once. Only pages belonging to the exact same host as the base URL are eligible for crawling—links pointing to other domains or subdomains are listed but ignored for traversal.

To keep the codebase lightweight, the crawler uses a straightforward pattern-based HTML link extractor instead of external parsing libraries, and enforces sensible resource limits such as maximum download size and content-type filtering. Error handling is intentionally minimal to keep command-line output focused on crawl results.

This repository also includes a suite of JUnit tests that validate key components such as URL normalization, host filtering, link extraction, and HTTP scheme validation. The project is structured as a standard Maven application, making it easy to build, test, and extend.

## Problem statement

Create a command line app that:

- Accepts a **base URL**.
- Crawls the site starting from that URL.
- For **each page it finds**, prints:
  - The URL of the page.
  - All URLs it finds on that page.
- The crawler will **only process that single domain**, and must **not crawl URLs pointing to other domains or subdomains**.
- Use patterns that allow the crawler to run as quickly as possible, without wasting compute resources.
- Do **not** use crawling frameworks like Scrapy or Playwright.

---

## How to build and run

### Prerequisites

- Java 17
- Maven

### Build

```bash
mvn clean package
```

This produces a runnable JAR in `target/`.

### Run

```bash
java -jar target/zego-java-crawler-1.0.0-SNAPSHOT.jar <base_url> [--concurrency N] [--max-pages N]
```

Examples:

```bash
# Default concurrency (10), max-pages (100)
java -jar target/zego-java-crawler-1.0.0-SNAPSHOT.jar https://example.com

# Increased concurrency and page limit
java -jar target/zego-java-crawler-1.0.0-SNAPSHOT.jar https://example.com --concurrency 32 --max-pages 500
```

### Output format

For each page crawled, the program prints to `stdout`:

1. The page URL.
2. One line per URL discovered on that page.
3. A blank line as a separator.

Example:

```text
https://example.com/
https://example.com/about
https://example.com/contact
https://external.com/

https://example.com/about
https://example.com/team
...
```

Only URLs with the **exact same host** as the base URL are enqueued for crawling. Links to other domains or subdomains may be printed but are **not** followed.

---

## Design overview

### High-level structure

The core is a single class `SimpleCrawler` that encapsulates:

- **Configuration**: base URL, concurrency, max pages, timeout, User-Agent.
- **State**:
  - `BlockingQueue<String> queue` of URLs to visit.
  - `Set<String> seen` (thread-safe) to avoid revisiting URLs.
  - `AtomicInteger pagesCrawled` to enforce a global `maxPages` limit.
- **HTTP client**:
  - Java 11+ `HttpClient` with redirect following and a global timeout.
- **Concurrency**:
  - A fixed-size `ExecutorService` where each worker repeatedly pulls URLs from the queue, fetches and parses them, and enqueues new same-host links.

### URL handling and domain restriction

- The constructor validates the base URL and extracts its host:

  ```java
  URI start = new URI(baseUrl);
  this.baseHost = start.getHost();
  ```

- `normalize(base, href)`:
  - Resolves relative URLs using `new URI(base).resolve(href)`.
  - Rejects non-HTTP(S) schemes.
  - Skips `mailto:`, `javascript:`, and other non-navigational schemes.
  - Strips fragments (`#section`) to reduce duplicates.

- `sameExactHost(url)`:
  - Extracts the host from the candidate URL and compares it to `baseHost` (case-insensitive).
  - Ensures that:
    - If the base is `https://example.com`, then `https://example.com/foo` is allowed.
    - `https://www.example.com/foo` and `https://sub.example.com/foo` are **not** crawled.

The crawler therefore strictly adheres to “single domain, no subdomains”.

### HTML parsing

For performance and to avoid extra dependencies, I chose a lightweight, regex-based approach:

```java
private static final Pattern HREF_PATTERN =
    Pattern.compile("(?i)<a[^>]+href=["']?([^"' >]+)", Pattern.CASE_INSENSITIVE);
```

The `extractLinks` method:

- Scans the HTML for `<a ... href="...">` patterns.
- Normalizes each `href` via `normalize`.
- Returns a unique, sorted set of absolute URLs.

**Trade-off:** this approach is fast and simple, but not as robust as a full HTML parser (e.g. Jsoup). It may miss some very unusual HTML constructs. For production-grade crawling I would likely use Jsoup instead.

### Concurrency model

The crawler uses:

- A `BlockingQueue<String>` of pending URLs.
- A fixed thread pool via `Executors.newFixedThreadPool(concurrency)`.

Each worker:

1. Retrieves a URL from the queue (blocking with timeout).
2. Fetches and parses the page.
3. Prints the URL and all discovered links.
4. Enqueues new URLs that:
   - Have not been seen before, and
   - Belong to the exact same host as the base URL.

Workers stop once:

- The global `maxPages` limit has been reached, and
- The queue has been drained for some time (no new URLs arriving).

This gives:

- Good parallelism for I/O-bound operations (HTTP requests).
- A simple mental model: each URL is visited at most once, and there is a clear, bounded worker pool.

### Performance and resource usage

- **Max body size** (`MAX_DOWNLOAD_BYTES = 2 MiB`) prevents a single large page from consuming too much memory.
- **Content-type filtering** skips non-HTML responses early.
- **Connection reuse**: using a single `HttpClient` instance per crawler allows keep-alive across requests.
- **Concurrency** is configurable:
  - Higher concurrency increases throughput but may put more load on both the crawler and the target site.
  - A sensible default of 10 threads is used if not overridden.

### Error handling

- Network errors, timeouts, and parsing exceptions are caught and ignored at page level.
- The crawler continues with other URLs in the queue.
- In a production setting I would add logging and error metrics; here I keep output focused on the exercise’s requirements.

---

## Testing

Tests are implemented with **JUnit 5**.

### Unit tests

I added unit tests for the core, deterministic parts of the logic:

- `normalize`:
  - Resolves relative URLs correctly.
  - Drops fragments.
  - Ignores `mailto:` and `javascript:` links.
  - Rejects non-HTTP(S) schemes.
- `sameExactHost`:
  - Accepts URLs that match the base host exactly.
  - Rejects subdomains and other domains.
- `extractLinks`:
  - Parses links from simple HTML snippets.
  - Returns absolute URLs after normalization.
- `isHttpish`:
  - Validates HTTP vs non-HTTP schemes.

These tests run without hitting the real network.

### Running tests

```bash
mvn test
```

---

## Tools, IDE, and AI usage

### Development environment

- **Language:** Java 17
- **Build tool:** Maven
- **IDE:** IntelliJ IDEA

### AI tools

I used the following AI tools while working on this exercise:

- **ChatGPT (OpenAI)**  
  - To discuss design options (e.g., concurrency patterns, URL normalization strategies).
  - To sanity-check my approach and think through potential edge cases and test ideas.
  - All final code was written, reviewed, and adapted by me.


---


## Why I Chose Java (and How This Could Also Be Implemented in Python)

Although this project can be completed in several languages, I chose to implement the crawler in Java because it is a language I am highly comfortable with—especially when working with concurrent, network-driven applications. Java’s concurrency model, thread pools, and mature standard libraries make it straightforward to build a fast, predictable, and efficient crawler without relying on heavy external dependencies. The modern Java HttpClient also offers reliable connection reuse, redirect handling, and configurable timeouts out of the box, which fits this problem very well.

That said, this solution could just as easily be implemented in Python. I have strong professional experience in Python (over two years), and the design I’ve used here translates naturally into a Pythonic implementation. Both languages support the same architectural principles:
- A queue of URLs to crawl
- A worker pool for concurrent fetching
- A set to track visited pages
- Domain filtering logic to prevent subdomain drift
- A link extraction component
- Configurable concurrency and max-page limits

### How This Could Be Implemented in Python

If I were to implement this crawler in Python, the overall structure would remain the same. The main difference would be in the concurrency model and HTML parsing libraries used.

Async approach (high performance)
For maximum throughput, I would use:
- asyncio for event-driven concurrency
- aiohttp for non-blocking HTTP requests
- asyncio.Semaphore for concurrency limits
- html.parser or BeautifulSoup for extracting links

This approach enables a large number of concurrent fetches with minimal overhead.

Threaded approach (closer to the Java version)
If simplicity and parity with the Java implementation were the goal, I would choose:
- ThreadPoolExecutor from concurrent.futures
- The requests library (or urllib) for HTTP fetching
- A shared queue and deduplication set

This closely mirrors the Java design while staying idiomatic to Python.

### Shared Architecture Across Both Languages

Regardless of whether the crawler is written in Java or Python, the high-level architecture stays the same:
- A URL scheduling queue
- A deduplication set
- Exact-domain filtering
- A parser that extracts links from HTML pages
- A concurrency controller
- A simple, clear CLI interface

Because the crawler’s logic is language-agnostic, porting this solution between Java and Python is straightforward, and both implementations would behave consistently.

## Possible extensions

If this were evolving into a more fully-featured system, I would consider:

- **Multiple domains / crawl jobs**
  - A manager component orchestrating multiple `SimpleCrawler` instances.
  - Shared worker pool with per-domain rate limits.
- **Non-CLI interface**
  - A small HTTP API (e.g. using Spring Boot) to submit crawl jobs, monitor progress, and retrieve results.
  - A simple web UI for visualizing the crawl graph.
- **robots.txt and sitemaps**
  - Fetch and parse `robots.txt` for each domain.
  - Respect disallow/allow rules.
  - Bootstrap URLs using `sitemap.xml` when available.
- **Storage and analysis**
  - Persist crawled pages and link graph to a database.
  - Provide query APIs (e.g., "Where is this URL referenced from?").
- **Politeness and throttling**
  - Per-host rate limiting and configurable delays.
  - Backoff strategies if the target site becomes slow or starts returning errors.
- **Richer URL canonicalization**
  - Normalizing trailing slashes and query strings.
  - Configurable deduplication rules.

The current CLI tool is intentionally lightweight and focused on satisfying the exercise requirements while demonstrating clean, modular, and concurrent code.

## Author

*   **[Chaitanya Potla](https://github.com/chaitanyapotla)** - Developer

## Contact

For questions or support, please contact:

*   **[Chaitanya Potla](https://github.com/chaitanyapotla)** - Email: [chaitanyadpsv@gmail.com](mailto:chaitanyadpsv@gmail.com)