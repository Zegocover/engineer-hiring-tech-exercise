# Zego Web Crawler – Technical Design Document

## 1. Overview

This document describes the technical design of a **single-domain, high‑performance web crawler** implemented as a **Python CLI application**. The crawler accepts a base URL, traverses all reachable pages within the same domain, and prints each page URL alongside the URLs discovered on that page.

The design prioritizes **correctness, performance, clarity, and extensibility**, while remaining intentionally constrained to the scope of the interview exercise.

---

## 2. Goals and Non‑Goals

### 2.1 Goals

- Crawl a website starting from a base URL
- Stay strictly within the same domain (no subdomains, no external domains)
- Avoid visiting the same URL more than once
- Maximize crawl speed without wasting compute resources
- Be resilient to transient failures
- Produce deterministic, testable behavior
- Provide a clean CLI interface

### 2.2 Non‑Goals

- JavaScript execution or browser‑level crawling
- Full internet‑scale crawling
- Distributed crawling across machines
- SEO‑grade canonicalization

---

## 3. Functional Requirements

- Accept a **base URL** from the command line
- For each visited page:
  - Print the page URL
  - Print all URLs discovered on that page
- Crawl **only the same domain** as the base URL
- Avoid infinite loops and circular paths
- Handle transient HTTP/network failures gracefully
- Avoid frameworks like Scrapy or Playwright

---

## 4. Assumptions and Constraints

- Pages may contain relative and absolute links
- The same content may be reachable via multiple URLs
- Network errors are expected and should not abort the crawl
- Memory is finite and must be protected by limits
- The crawler runs on a single machine

---

## 5. High‑Level Architecture

```
+------------------+
| CLI Entry Point  |
+--------+---------+
         |
         v
+------------------+
|  Crawler         |
|  (Coordinator)   |
+----+--------+----+
     |        |
     v        v
+---------+  +-------------+
| Queue   |  | Worker      |
| (BFS)   |  | (Async)     |
+---------+  +-------------+
```

The crawler follows a **BFS (breadth‑first search)** model using an in‑memory queue and asynchronous workers.

---

## 6. Core Design Decisions

### 6.1 Concurrency Model

- **AsyncIO + aiohttp** for non‑blocking I/O
- Controlled concurrency via:
  - Configurable batch size
  - Connection limits in aiohttp

**Rationale:**
- I/O‑bound workload
- Predictable resource usage
- No thread coordination overhead

---

### 6.2 Crawl Strategy

- **Breadth‑First Search (BFS)**
- URLs are processed in batches
- New URLs are enqueued only after validation

**Benefits:**
- Fair traversal of site structure
- Natural depth control
- Easier memory accounting

---

### 6.3 URL Deduplication

- Maintain an in‑memory `scheduled` set to avoid enqueueing duplicates
- Maintain an in‑memory `visited` set for successfully fetched URLs
- Normalize URLs before comparison

This prevents:
- Circular crawling
- Infinite loops
- Duplicate work

---

### 6.4 Domain Restriction

- Parse URLs using `urllib.parse`
- Allow only URLs whose `netloc` exactly matches the base domain for **crawling**
- Explicitly exclude subdomains
- Still **print all discovered links**, including external ones

---

## 7. Component Design

### 7.1 CLI Entry Point

**Responsibilities:**
- Parse and validate arguments
- Initialize the crawler
- Defer crawl execution to `Crawler`

**Parameters:**
- `url` (required): base URL
- `--output` (optional): output file (same text format as stdout)
- `--quiet` (optional): suppress stdout (useful with `--output`)
- `--batch-size` (optional): max parallel requests (min 1, max 10)
- `--max-urls` (optional): safety limit (min 1, max 1000)
- `--timeout` (optional): per-request timeout in seconds (default 5, min 0, max 10)
- `--retries` (optional): retry count for transient failures (min 0, max 3)

**Testing Focus:**
- Argument validation
- Correct wiring of components

---

### 7.2 Crawler

**Role:** Orchestrator for a single crawl session

**Responsibilities:**
- Maintain BFS queue
- Track scheduled vs. visited URLs
- Schedule batches
- Aggregate results
- Handle retries and failures
- Emit progress logs

**Behavior Notes:**
- URLs are marked visited only after a successful fetch; failures are retried via re-queueing until the retry limit is reached.

**Current Implementation Status:**
- Async crawl loop implemented
- Retries are handled in `Crawler` by re-queueing failed URLs
- Output is emitted after crawl completes (stdout + optional file)
- A shared `aiohttp` session is reused across requests

**Key Properties:**
- Single‑domain invariant
- Deterministic traversal
- Output I/O is deferred until the crawl completes
- Single‑use instance per crawl

**Testing Focus:**
- Queue behavior
- Deduplication logic
- Retry handling
- Constructor validation for bounds
- Single‑use guard behavior
- Output formatting and logging signals

---

### 7.3 Worker

**Role:** Pure async unit of work for a single URL

**Responsibilities:**
- **HTTP Fetch**
  - Issue GET with timeouts (retry policy handled by `Crawler`)
  - Accept redirects, but only follow within HTTP/S
  - Capture status code and content type
- **HTML Parse**
  - Parse only when content appears to be HTML
  - Use BeautifulSoup with the built-in HTML parser
- **URL Discovery**
  - Extract `<a href>` links
  - Normalize (resolve relatives, drop fragments)
  - Deduplicate per page before returning
  - Return both **all links** and **same-domain crawlable links**
- **Return structured result**
  - `url`, `links`, `crawlable_links`, `status`, `error` (if any)

**Explicit Design Choice:**
> Worker does **not** print or mutate global state

This avoids side effects inside async code and makes the worker easy to test.

**Testing Focus:**
- HTML fetching (mocked)
- Link extraction
- Error propagation

---

## 8. Error Handling Strategy

- Best‑effort crawl
- Explicit `Result` type per page
- Small retry count for transient failures
- Failures are recorded and reported

The crawler never aborts the entire process due to a single page failure.

---

## 9. Libraries and Tooling

- **aiohttp** – async HTTP client
- **BeautifulSoup** – HTML parsing
- **urllib.parse** – URL normalization
- **AsyncIO** – concurrency model
- **Poetry** – dependency and project management
- **pytest** – testing

---

## 10. Design Principles

### Primary Principles

- KISS (Keep It Simple)
- YAGNI (You Aren’t Gonna Need It)
- Least Surprise
- Correctness > Cleverness
- Functional style where it improves clarity

### Secondary Principles

- DRY
- SOLID (applied pragmatically)
- Clean Architecture (lightweight)

---

## 11. Performance Considerations

- Asynchronous I/O avoids blocking
- Batching limits memory and connection pressure
- Early filtering of invalid URLs
- No unnecessary object retention

---

## 12. Extensibility Considerations

### Considered but Deferred

- Multi‑stage Worker pipeline
- Persistent queue using SQLite
- Multi‑domain crawling
- Web UI (e.g., Streamlit)

These were intentionally excluded to avoid over‑engineering but can be added without major refactors.

---

## 13. Future Improvements

- Persistent crawl state for resume/recovery
- Smarter URL canonicalization
- Robots.txt support
- Rate‑limiting policies
- Structured output schemas
- Containerized deployment (Docker)

---

## 14. Summary

This design delivers a **fast, safe, and testable crawler** aligned with production engineering principles while remaining intentionally simple. The architecture demonstrates clear ownership boundaries, explicit trade‑offs, and strong extensibility without unnecessary complexity.

---

## 15. Dockerization Discussion

Containerization is a natural next step for reproducible runs and simplified onboarding. A minimal container would:
- Install runtime dependencies
- Copy the crawler source
- Execute the CLI as the entrypoint

**Why it was not implemented in this exercise:**
- The focus was on crawler correctness, performance, and testability within the time box.
- Docker setup would be straightforward but adds packaging/ops concerns outside the core requirements.

If needed, a slim image could be added without impacting the crawler architecture.
