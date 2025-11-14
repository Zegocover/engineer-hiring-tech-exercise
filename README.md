# Zego Web Crawler (Kotlin)

A simple, fast, domain-scoped web crawler written in Kotlin.  
It prints every discovered URL in real time while crawling a single website.

---

## Architecture

The crawler is composed of four focused components:

### **Fetcher**

- Performs HTTP GET requests
- Handles timeouts, retries, and exponential backoff
- Special-case handling for `429 Retry-After`
- Detects whether the response is HTML

### **UrlNormalizer**

- Converts relative or absolute links into canonical absolute URLs
- Drops fragments and unsupported schemes
- Ensures URLs remain within the same domain
- Prevents duplicates through normalization

### **LinkParser**

- Extracts all meaningful `href` attributes using Jsoup
- Filters out empty, malformed, or script-based links

### **Crawler**

- Fixed-size worker pool (Producer–Consumer model)
- BFS crawling using a thread-safe queue
- Synchronized visited set
- Prints URLs in real time as they are discovered
- Graceful shutdown when no work remains

---

## How to Run

```bash
./gradlew run --args="https://example.com"

## Implementation Summary

This project implements a domain-scoped, concurrency‑aware web crawler in Kotlin with a clean, testable architecture.  
Below is a high‑level summary of the design decisions and the work completed.

### What Has Been Implemented

#### 1. Modular Architecture
The crawler is composed of four focused components:
- **Fetcher** - Performs HTTP requests and returns raw HTML.
- **UrlNormalizer** - Resolves URLs, enforces same‑domain rules, removes duplicates through canonicalization.
- **LinkParser** - Extracts structured links from HTML using Jsoup.
- **Crawler** - Orchestrates fetching, parsing, and traversal using BFS and a concurrency‑limited worker.

This separation allows each piece to be tested independently and extended easily.

#### 2. Concurrency Model
The crawler uses:
- `coroutineScope` for structured concurrency
- `Semaphore` to enforce a strict `maxConcurrency`
- A single worker coroutine consuming from a thread‑safe queue  
  This avoids race conditions and ensures deterministic behaviour in tests.

#### 3. Visited Set + Queue
A thread‑safe `ConcurrentHashMap.newKeySet()` is used to prevent re‑visiting URLs.  
The queue implements BFS, which is more memory‑stable and predictable compared to DFS.

#### 4. Full Test Suite
A comprehensive set of **unit tests** and **integration tests** was created:
- Normalizer tests (including parameterized cases)
- LinkParser tests
- Fetcher behaviour tests
- Crawler logic tests (BFS, dedupe, domain filtering, concurrency limit)
- Full integration test using an in‑memory HTTP server and fake parser

These ensure correctness, isolation, and regression safety.

#### 5. Production‑Ready Design Choices
- OkHttp for robust HTTP handling  
- Jsoup for safe HTML parsing  
- Clear separation of pure logic vs. side effects  
- Deterministic behaviour suitable for CI testing  
- Simple CLI entry point using Kotlin's `main`  

### Possible Extensions
Given more time, this crawler could be extended to:
- Crawl multiple domains concurrently
- Persist crawl results to a database or Kafka
- Add robots.txt support
- Implement distributed work queues
- Provide a web UI or REST API wrapper
- Export metrics with OpenTelemetry

---

This summary describes the approach, trade‑offs, and key decisions in the implementation, making the project easy to review and understand.