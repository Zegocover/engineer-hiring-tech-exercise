# Proposal

## Why

The Zego Python exercise (`engineer-hiring-tech-exercise/python/README.md`) asks for a command-line app that crawls one domain from a base URL and prints every page it visits with all the URLs found on that page. It must be as fast as possible without wasting accuracy or compute, and must not use Scrapy or Playwright. We also want the crawler to be a reusable package, so consumers can supply their own way of fetching, parsing and storing pages without changing the crawl logic. That is the base for the longer-term system in our design diagram (webserver, visualiser, datastore).

## What Changes

- Add a new installable Python package (in `engineer-hiring-tech-exercise/python/`) with a crawler that:
  - starts from a base URL
  - follows links only on the exact same host
  - fetches pages concurrently up to a fixed limit
  - reports each page's URL with every link found on it, including off-domain links
- Define three public extension points that consumers can implement: **fetching** pages, **parsing** links out of a page, and **writing** results. The package ships default implementations of each.
- Keep the URL frontier (queue of pages to visit plus set of URLs already seen) as internal state of the crawl manager, not a public extension point.
- Keep these inside the package, never delegated to consumer code: URL resolution and normalisation, de-duplication, same-host scope, crawl termination and error policy.
- Add a `crawl` command-line entry point that wires the defaults together. It has options for concurrency, page/depth limits, timeouts, `robots.txt` handling and output format (text or JSON Lines).
- Add a test suite (unit tests plus an end-to-end crawl of a fake site) and production-style project tooling (packaging, lint, type-check, CI).
- Extend the exercise README with the design discussion, trade-offs and AI-tool usage required by the brief.

**Assumptions recorded for this change (proposed defaults, adjustable later):**
- "URLs on a page" means `<a href>` links only.
- `www.example.com` and `example.com` are different hosts.
- `robots.txt` is respected by default and can be turned off with a flag.

**Out of scope:** datastore/SQL writer, webserver, visualiser, React frontend, a pluggable/distributed frontier, multi-domain crawling. These are covered as a design note in the README only.

## Capabilities

### New Capabilities

- `site-crawl`: Crawling a single host from a base URL and reporting each visited page with its links. Covers scope rules, URL normalisation, de-duplication, limits, error handling, termination, output formats and the command-line interface.
- `crawler-extension-api`: The public contract that lets a consumer replace how pages are fetched, how links are parsed and how results are written, while the package keeps ownership of crawl correctness.

### Modified Capabilities

(none, since there are no existing specs)

## Impact

- **New code:** `engineer-hiring-tech-exercise/python/` (package source, tests, `pyproject.toml`). The OpenSpec planning folder sits in the parent folder, outside that git repo.
- **New runtime dependencies:** an async HTTP client and a fast HTML parser (chosen in design.md).
- **New dev dependencies:** test runner with async support, HTTP mocking, linter, type checker.
- **Docs:** `engineer-hiring-tech-exercise/python/README.md` is extended, as the brief requires.
- **No existing code or APIs are affected** (greenfield).
