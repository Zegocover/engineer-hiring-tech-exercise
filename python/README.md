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

---

# Solution: Site Crawler

A fast, single-domain web crawler. Given a base URL, it visits every page on
that domain and prints each page's URL along with all the links found on it.
Links pointing to other domains (and, by default, subdomains) are reported but
not followed.

Built with `asyncio` + `httpx` for concurrency and BeautifulSoup + `lxml` for
parsing.

## Requirements

- Python **3.13**
- [Poetry](https://python-poetry.org/) for dependency management

## Installation

```bash
cd python
poetry install
```

## Usage

```bash
poetry run crawl https://example.com/
```

The scheme is optional and defaults to `https`, so `poetry run crawl example.com`
works too. You can also run it as a module: `poetry run python -m crawler <url>`.

### Options

| Flag | Default | Description |
| --- | --- | --- |
| `url` (positional) | — | Base URL to start crawling |
| `-c`, `--concurrency` | `10` | Number of pages to fetch in parallel |
| `--timeout` | `10.0` | Per-request timeout (seconds) |
| `--max-pages` | none | Stop after crawling this many pages |
| `--include-subdomains` | off | Also crawl subdomains of the base host |
| `--user-agent` | `site-crawler/…` | `User-Agent` header to send |
| `--json` | off | Emit JSON Lines instead of text |
| `-v`, `--verbose` | off | Log each page as it is crawled (to stderr) |
| `--version` | — | Print the version and exit |

### Output

Results go to **stdout**; the run summary and any diagnostics go to **stderr**,
so stdout stays clean for piping.

Text (default) — each page's URL followed by its indented links:

```
https://example.com/
  https://example.com/about
  https://example.com/contact
  https://external.example.org/partner
```

JSON Lines (`--json`) — one object per page, easy to pipe into `jq`:

```json
{"url": "https://example.com/", "status": 200, "error": null, "links": ["https://example.com/about"]}
```

## How it works

The code is deliberately split into small, single-responsibility units wired
together by dependency injection, which is what makes it easy to test each part
in isolation and to swap the entry point later (see [Extending](#extending-the-crawler)).

| Module | Responsibility |
| --- | --- |
| [`url.py`](src/crawler/url.py) | Pure functions: URL normalization, scheme filtering, same-site scoping |
| [`fetcher.py`](src/crawler/fetcher.py) | HTTP concern behind a `Fetcher` protocol; `HttpxFetcher` streams responses |
| [`extractor.py`](src/crawler/extractor.py) | HTML → resolved, de-duplicated absolute links |
| [`crawler.py`](src/crawler/crawler.py) | Async orchestrator: worker pool, frontier, dedup, scoping |
| [`output.py`](src/crawler/output.py) | `TextWriter` / `JsonWriter` output sinks |
| [`config.py`](src/crawler/config.py) | `CrawlConfig` — one immutable object of tunables |
| [`cli.py`](src/crawler/cli.py) | `argparse` front end that wires the above together |

Control flow:

```
base URL → normalize → frontier queue
                          │
        ┌─────────────────┴─────────────────┐  (N worker coroutines)
        ▼                                     ▼
   fetch (httpx)                         fetch (httpx)
        │                                     │
   extract links                         extract links
        │                                     │
   emit PageResult ──► results queue ──► CLI prints
        │
   schedule same-site, unseen links back onto the frontier
```

## Design decisions & trade-offs

**Concurrency: `asyncio` + a fixed worker pool.** Crawling is I/O-bound (most
time is spent waiting on the network), so `asyncio` lets us keep many requests
in flight cheaply on a single thread. The concurrency limit is simply the number
of worker coroutines draining a shared `asyncio.Queue`; the pool size *is* the
cap on in-flight requests, so no separate semaphore is needed. Because everything
runs on one event-loop thread, the `visited` set needs no locking. Termination
uses `Queue.join()`: each worker enqueues a page's followable links *before*
calling `task_done()`, so the queue's unfinished count only reaches zero once the
whole reachable graph is processed, at which point a watcher task stops the
result stream. The alternative — threads + `requests` — is simpler to explain but
caps throughput lower and needs explicit locking so the async approach was chosen.
This kept the components small enough that the async surface stays contained.

**Streaming, resource-conscious fetches.** `HttpxFetcher` streams responses and
only downloads a body when the response is HTML with a non-error status — a large
PDF or image costs a round-trip of headers, not a full download. The retained
body is capped at `max_bytes` so one pathological page can't exhaust memory. One
honest trade-off: rather than aborting an oversized HTML body mid-stream (which
leaks httpx's internal byte generators and is awkward to close cleanly), we drain
the stream but cap what's kept. Memory stays bounded; we may still read an
oversized HTML body off the wire, which is acceptable given non-HTML is already
skipped and read timeouts bound pathological cases.

**URL normalization — accuracy over aggressive deduping.** `normalize()` applies
only transformations that can't merge two genuinely different resources: strip
fragments, lower-case scheme and host, drop default ports, canonicalize an empty
path to `/`, and resolve `.`/`..` segments (RFC 3986 §5.2.4). It deliberately
does **not** strip trailing slashes, reorder query parameters, or normalize
percent-encoding case, because those can denote different pages and the brief
prioritizes accuracy. The cost is that `/a` and `/a/` are treated as distinct and
may both be crawled which was considered safer than silently conflating pages.

**`www` counts as the apex domain; other subdomains don't.** `www.example.com`
and `example.com` are treated as one site (matching real-world expectations),
while `blog.example.com` is excluded unless `--include-subdomains` is passed. The
brief excludes subdomains, and this is the least surprising reading of it.

**Print all links found, follow only same-site ones.** Each page lists every link it 
contains, including external ones. The crawler only follows links that are on the same 
site and haven't been visited yet. Link extraction simply resolves and deduplicates 
links, while the crawler handles URL normalization and deciding which links to crawl. 
This keeps each component responsible for one job.

**Error handling.** A transport error, an HTTP error status, or even an unexpected
exception in a worker is turned into a `PageResult` with an `error`/status rather
than aborting the crawl — one bad page never stops the run.

**Redirects.** Redirects are followed; links are resolved against the final
(post-redirect) URL, and the redirect target is marked visited so it isn't
re-fetched. A same-site page that redirects off-domain is reported but its body
is not mined for links, respecting the single-domain rule.

## Testing

```bash
poetry run pytest          # runs the suite with coverage
poetry run ruff check .    # lint
poetry run ruff format .   # format
poetry run mypy            # strict type checking
```

The suite has **100% line coverage** and mixes two levels:

- **Unit tests** with mocked HTTP (`respx`) and an in-memory `FakeFetcher`, so
  traversal, normalization, domain filtering, duplicate/cycle detection and error
  handling are verified deterministically and offline. URL logic is exercised
  with large table-driven cases (the most bug-prone area).
- An **integration test** ([`test_integration.py`](tests/test_integration.py))
  that stands up a real `ThreadingHTTPServer` serving a known link-graph — with
  cycles, a redirect, a non-HTML resource, a 404 and an off-domain link — and
  drives the real fetcher/extractor/crawler over actual HTTP.

The network layer sits behind a `Fetcher` protocol precisely so it can be faked;
that single design choice is what keeps the tests fast and hermetic.

## Possible extensions

One practical extension would be to add a crawl summary at the end of each run.
Rather than only printing the links discovered on each page, the crawler could also 
report useful statistics such as:

- Total pages discovered
- Total pages successfully crawled
- Internal vs external links found
- Pages skipped because they had already been visited
- Pages skipped because they were outside the allowed domain
- Broken links (4xx/5xx responses)
- Total crawl duration and average pages processed per second

Although this solution is designed as a command-line application, the crawler itself 
is implemented as a reusable library, making it straightforward to support more 
advanced scenarios.

To crawl multiple domains at once, I would introduce a `CrawlManager` responsible for 
coordinating a separate crawl state (frontier and visited URLs) for each domain while 
sharing a bounded pool of workers. This would allow multiple sites to be crawled 
concurrently without exceeding a configured level of concurrency or allowing one large 
site to monopolise resources. At this scale, it would also become important to respect 
robots.txt, apply per-host rate limiting, back off after receiving HTTP 429 or 503 
esponses, and move the frontier and visited set into shared storage (for example Redis) 
so crawls can be resumed and distributed across multiple worker processes.

While a command-line interface is appropriate for this exercise, it would not be 
the best long-term interface for a production crawler. A service exposing an API would 
allow crawl jobs to be started, monitored and cancelled remotely, while a message queue 
and worker pool could distribute work across multiple machines. Crawl results could be 
streamed to downstream systems or persisted in a database rather than printed to standard 
output, enabling scheduled, resumable and scalable crawling.

Given more time, I would also add support for `robots.txt` and `sitemap.xml`, implement 
retries with exponential backoff, detect duplicate content by comparing page hashes, 
and add structured logging, metrics and tracing to improve observability.

## Tooling & AI-assisted workflow

- **Editor / IDE:** VS Code 
- **AI assistant:** ChatGPT for design ideation and Claude Code (Claude Opus
  4.8) for planning and implementation, used as an interactive pair-programmer from the terminal.
- **Language & tooling:** Python 3.13, Poetry, `ruff` (lint + format), `mypy`
  (strict), `pytest` + `pytest-asyncio` + `respx` + `pytest-cov`, `pre-commit`,
  and GitHub Actions CI.

**How AI was used.** 

The work ran in explicit phases rather than
"generate-it-all": 

1. An ideation pass listing requirements, constraints and
implementation options with trade-offs.
2. A decision round pinning down the open design questions (concurrency model, `www` policy, output scope). 
3. A concrete plan with module responsibilities and a test matrix.
4. Test-first implementation, one module at a time, with `ruff`/`mypy`/`pytest` run as a gate
after every step and the CLI verified against a live site. AI accelerated
boilerplate, surfaced edge cases (RFC 3986 dot-segments, off-domain redirects,
httpx stream cleanup) and drafted tests. 

Every design decision was reviewed and signed off deliberately, and the trade-offs above reflect real choices made during development rather than defaults accepted blindly.
