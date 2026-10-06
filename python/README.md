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
4. Add us (@nktori, @danyal-zego, @bogdangoie, @cypherlou, @marliechiller, @ZEGODiogoAlves, and @BarryMcAuley) as collaborators and tag us to review.
5. Notify your TA so they can chase the reviewers.

---

# Solution: `site-crawler`

A fast crawler for a single host, packaged as a library with a `crawl` command-line tool. Consumers can replace how
pages are **fetched**, how links are **parsed** and where results are **written** without touching the crawl
logic.

## Quick start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
cd python
uv sync
uv run crawl https://books.toscrape.com/ --max-pages 20
```

Each page is printed with the links found on it, indented beneath it. Logs and a summary go to stderr, so stdout
can be piped:

```text
https://books.toscrape.com/
  https://books.toscrape.com/index.html
  https://books.toscrape.com/catalogue/category/books_1/index.html
  ...
Crawled 20 pages (20 fetched, 0 errors, 0 blocked by robots.txt) in 1.84s
```

| Option | Default | Meaning |
|---|---|---|
| `-c, --concurrency N` | 16 | parallel requests (also the HTTP connection pool size) |
| `--max-pages N` | unlimited | fetch at most N pages |
| `--max-depth N` | unlimited | follow links at most N hops from the base URL |
| `--timeout S` | 10 | per-request timeout in seconds |
| `--no-robots` | off | ignore `robots.txt` |
| `--format text\|jsonl` | text | `jsonl` prints one `{"url": ..., "links": [...]}` object per line |
| `--user-agent S` | `site-crawler/0.1` | User-Agent header |
| `-v` / `-vv` | warnings | info / debug logging |

Exit codes: `0` on success (even if some pages failed), `1` if the base URL could not be fetched, `2` for invalid
arguments.

### Development

```bash
uv run ruff check && uv run ruff format --check   # lint + format
uv run mypy                                       # strict type-check (src, tests, examples)
uv run pytest                                     # 100+ tests, no network needed
```

CI (`.github/workflows/ci.yml`) runs these steps on Python 3.12 and 3.13. Pre-commit hooks are in
`.pre-commit-config.yaml`.

## Using it as a library

```python
from site_crawler import CrawlConfig, Crawler, PageResult


class MyWriter:  # no base class needed
    async def write(self, result: PageResult) -> None:
        print(result.url, len(result.links))  # e.g. insert into a database instead

    async def aclose(self) -> None:
        pass


stats = await Crawler(CrawlConfig("https://example.com/", max_pages=100), writer=MyWriter()).run()
```

Any of `fetcher=`, `parser=` and `writer=` can be passed. Whatever is left out uses the default (`HttpxFetcher`,
`SelectolaxParser`, `TextWriter`). The defaults and `JsonLinesWriter` can also be imported from `site_crawler`, so
they can be combined with a custom component. [`examples/custom_writer.py`](examples/custom_writer.py) builds a link graph
and reports the most-linked URLs:

```bash
uv run python -m examples.custom_writer https://books.toscrape.com/ 20
```

## Architecture

```
            +-------------------------- Crawler.run() ---------------------------+
            |                                                                    |
 base URL --+--> _enqueue --> asyncio.Queue[(url, depth)] ----+                  |
            |       ^   (seen-set, same host, depth,         |                  |
            |       |    page budget, robots.txt)            v                  |
            |       |                         N workers: Fetcher.fetch()         |
            |       |                                    Parser.parse()          |
            |       +--------- normalised links <-------- resolve + normalise    |
            |                                               |                    |
            |                                               v                    |
            |                          asyncio.Queue[PageResult] (bounded)       |
            |                                               |                    |
            |                                               v                    |
            |                          1 writer task: Writer.write()             |
            +--------------------------------------------------------------------+
```

```
src/site_crawler/
  __init__.py              public API (everything below a consumer needs)
  cli.py                   the `crawl` command
  models/                  data exchanged between components
    fetch.py               FetchResult
    page.py                PageResult
    config.py              CrawlConfig, ConfigError (validated, immutable)
    stats.py               CrawlStats
    errors.py              FetchError
  interfaces/              what consumers implement
    fetcher.py             Fetcher
    parser.py              Parser
    writer.py              Writer
  fetchers/                default implementations, grouped by role
    httpx_fetcher.py       HttpxFetcher
  parsers/
    selectolax_parser.py   SelectolaxParser
  writers/
    text.py                TextWriter
    jsonl.py               JsonLinesWriter
  core/                    the crawl engine
    crawler.py             Crawler: frontier, workers, writer task, error policy
    urls.py                resolve / normalise / same-host
    robots.py              robots.txt gate
```

Each layer only imports the layers before it:
`models <- interfaces <- fetchers / parsers / writers <- core <- cli`.
`tests/test_package.py` enforces this, and also checks that every subpackage imports on its own in a fresh
interpreter, so import cycles can't creep in. A new component, such as a database writer, has an obvious home:
`writers/sql.py`.

## Design decisions and trade-offs

The planning artefacts (proposal, behaviour specs with testable scenarios, design and task list) were written
before the code, using [OpenSpec](https://github.com/Fission-AI/OpenSpec). The main points:

**1. Async I/O with a fixed pool of workers.** Crawling is almost entirely waiting on the network, so `asyncio`
gives high concurrency on one thread with no locking. A fixed pool of N workers pulling from a queue keeps memory
and open sockets bounded, unlike `gather()` over a growing list of tasks. One `httpx.AsyncClient` is shared, so
connections are kept alive and pooled, with its connection limit matching the concurrency.
*Considered:* threads (GIL overhead, locking needed for the seen-set) and multiprocessing (too heavy for I/O-bound
work).

**2. Identical workers plus a single writer, rather than separate fetch/parse/write pools.** My first sketch had a
separate worker type for each stage. Parsing with selectolax takes microseconds, so extra queue hand-offs would
add latency and complexity for no gain. Each worker does fetch, then parse, then enqueue. Exactly one writer task
consumes results, so output never interleaves and consumer writers never need locking. The bounded results queue
applies backpressure if the writer is slow.

**3. The frontier is private state with a simple de-duplication rule.** The frontier is a queue plus a seen-set.
A URL is marked seen when it is *queued*, not when it is fetched. The check and the insert happen with no `await`
between them, so on a single-threaded event loop two workers can never fetch the same URL. `queue.join()` signals
completion, and every worker calls `task_done()` in a `finally` block so a failure can't hang the crawl (there's a
test for this). I kept the frontier out of the public interface on purpose: it's the part that would need to move
into shared storage for distributed crawling (see below), and exposing it now would be premature abstraction.

**4. Extension points are `typing.Protocol`s, and the crawler owns correctness.** Consumers implement
`Fetcher`, `Parser` and `Writer` structurally, with no inheritance (the example and tests use plain classes). A
parser only returns *raw* href strings. The crawler resolves them against the final URL after redirects,
normalises, filters and de-duplicates them, so a buggy parser can get extraction wrong but can never make the
crawl leave the host or fetch a page twice. *Considered:* ABCs, which report a missing method when the object is
created but force the consumer to inherit from package classes.

**5. Errors.** A `FetchError` (network failure, timeout or HTTP error after retries) is logged and counted, and the
crawl continues. Any *other* exception from a component is treated as a bug: the crawl stops, the writer and
fetcher are still closed, and the exception reaches the caller. Silently swallowing it would produce partial
output that looks complete. Retries live in the HTTP fetcher (exponential backoff with jitter, honouring
`Retry-After`, for timeouts, connection errors, 429 and 5xx) because they're protocol-specific.

**6. Libraries.** `httpx` for its mature, typed async API and good test tooling (`respx`); `aiohttp` is slightly
faster but weaker on both. `selectolax` (Lexbor) for parsing: many times faster than BeautifulSoup and
HTML5-compliant on malformed markup. Bodies are only downloaded for textual responses and are capped at 10 MB, so
PDFs and images cost a request but no bandwidth.

**7. Normalisation is conservative.** The crawler lowercases scheme and host, drops default ports and fragments,
and turns an empty path into `/`. It does *not* strip trailing slashes or sort query parameters, because either can
change which resource a server returns. I chose accuracy over a few saved requests.

### Interpretations of the brief

- **"All the URLs it finds on the page"** means `<a href>` links, including off-domain ones (reported but not
  followed). `<link>`, `<img>` and `<script>` are resources, not navigation, so they're excluded.
- **"Not subdomains"** means an exact host match, so `www.example.com` is a *different* host from `example.com`.
  Scheme is ignored, so `http://` and `https://` links on the crawl host are in scope.
- **robots.txt** is respected by default (except for the base URL, which the user asked for explicitly).
  Disallowed URLs are still reported as links on the pages that contain them. `Crawl-delay` is not honoured.
- When a redirect lands on a page that is already queued, the page is reported once, under its final URL.

## Testing

- **Unit tests** cover URL handling, config validation, each default component (`respx` mocks HTTP: retries,
  redirects, timeouts, body cap), the package layering (`tests/test_package.py`), and the crawl engine using
  in-memory fakes (`tests/fakes.py`): cycles, de-duplication
  under concurrency, limits, redirects, non-HTML responses, robots.txt and the error policy.
- **An end-to-end test** (`tests/test_end_to_end.py`) crawls a mocked site through the *real* fetcher and parser:
  a cycle, an internal redirect, an off-host redirect, a PDF, an external link, a 500 page and a robots-disallowed
  path. It caught a real bug: the fetcher skipped `text/plain` bodies, which silently emptied `robots.txt`.
- **CLI tests** check stdout, stderr and exit codes. The tests need no network access.

## Scaling beyond one site and the CLI

A command-line tool suits one-off crawls of a single site. To crawl many domains continuously, I would turn this
into a service:

```
 React UI --> API (FastAPI) --> job queue (per-domain partitions) --> crawler workers (this package)
                  |                                                        |
                  +----------------- results DB / visualiser <-------------+
```

- **Job API** instead of CLI arguments: submit, monitor and cancel crawls, and get results on demand. A web UI or
  visualiser reads from the database.
- **Shared frontier:** move the queue and seen-set into Redis (or a Bloom filter for memory) so stateless workers
  can scale out. This is the frontier interface I deliberately didn't extract yet.
- **Per-domain politeness:** partition work by host, with rate limits and `Crawl-delay` per domain, so many sites
  are crawled concurrently while each one is visited slowly.
- **Storage** is just another `Writer`. A natural schema is `pages(id, domain, url UNIQUE, status, fetched_at)` plus
  `links(source_page_id, target_url)` as a list of link edges between pages.

## Future work

- Per-host request rate limiting and `Crawl-delay`.
- Sitemap discovery as extra seeds. Optional `<link rel=canonical>` handling to merge duplicate pages.
- Running a slow consumer parser off the event loop (`asyncio.to_thread`) if profiling shows parsing blocks the
  workers.
- Resumable crawls: persist the frontier so an interrupted crawl can continue.
- HTTP/2 (`httpx[http2]`) for sites that support it.

## Tools and AI usage

- **IDE:** Visual Studio Code.
- **AI:** Claude Code (Anthropic's agentic coding assistant, running in the VS Code extension) with the OpenSpec
  workflow:
  1. `/opsx:explore` to talk through the design: I brought a draw.io architecture sketch (manager, request/parse/
     write workers, datastore, web UI), and the discussion simplified it to the design above (identical workers,
     the frontier kept private, storage as a `Writer`, the web parts kept as the scaling story).
  2. `/opsx:propose` to generate the proposal, the specs (behaviour scenarios that became test cases), the design
     and the task list.
  3. `/opsx:apply` to implement the tasks in order, with lint, type-check and tests run after each task.
- **Verification:** every task had a concrete check; ruff, mypy `--strict` and pytest run in CI; and the crawler
  was smoke-tested against https://books.toscrape.com/.
