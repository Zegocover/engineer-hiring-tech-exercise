# Single-host web crawler

Java 21 command-line crawler for the Zego engineering exercise.

It accepts a starting URL, visits pages on that exact host, and prints each page URL together with every HTTP link found on it. Other hosts and subdomains are printed when they appear as links, but they are never fetched.

```bash
./gradlew shadowJar
java -jar build/libs/crawler.jar https://example.com
./run_crawler.sh example.com -c 20 -t 15
```

If the URL has no scheme, `https://` is added.

## Development environment and tools

- **Language:** Java 21, chosen because it is an officially supported language for the exercise and because virtual threads keep concurrent I/O simple.
- **IDE:** IntelliJ IDEA Community Edition. Gradle import, JUnit run configurations, and the debugger were used while reading each commit.
- **Build:** Gradle 9.8.1 with the Gradle Wrapper, Shadow (fat jar), Spotless + palantir-java-format, Checkstyle, and Error Prone. Compiler warnings are errors.
- **Libraries:** `java.net.http.HttpClient` for HTTP, Jsoup for HTML parsing only, picocli for the CLI. No crawler framework.
- **Tests:** JUnit 5 and AssertJ. HTTP tests use the JDK `HttpServer`. Crawler tests use an in-memory fake fetcher. No test hits the public internet.
- **AI workflow:** Cursor was used as a pair-programming assistant. Each unit was designed first, implemented as a small commit, explained, and only then committed. I did not copy another candidate’s solution. The Zego evaluation harness (PR #26, not merged) was used as an acceptance check, not as the design.

## How to run

```bash
cd java
./gradlew test
./gradlew shadowJar
java -jar build/libs/crawler.jar --help
java -jar build/libs/crawler.jar https://example.com --concurrency 10 --timeout 10
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `-c`, `--concurrency` | 10 | Parallel fetches |
| `-t`, `--timeout` | 10s | Per-request timeout |
| `--max-depth` | 64 | Distance from the seed |
| `--max-redirects` | 5 | Redirect hops per request |
| `--max-response-bytes` | 2_000_000 | HTML size cap |
| `--user-agent` | `ZegoCrawler/0.1` | Request identity |

Page results go to stdout. The summary goes to stderr so results can be redirected on their own:

```bash
java -jar build/libs/crawler.jar https://example.com > pages.txt
```

## Architecture

The crawl is a pipeline. Each stage has an interface so the coordinator does not depend on Jsoup, `HttpClient`, or stdout.

```text
CLI (picocli)
  -> CrawlSettings
  -> CrawlRunner (composition root)
       -> Crawler
            -> Frontier          next URL + already seen
            -> PageFetcher       HTTP GET
            -> LinkExtractor     HTML -> links
            -> CrawlScope        may we fetch this host?
            -> CrawlListener     print the page
```

| Type | Implementation | Replace later with |
| --- | --- | --- |
| `Frontier` | `InMemoryFrontier` | Redis set + list |
| `PageFetcher` | `HttpPageFetcher` | retrying / rate-limited decorator |
| `LinkExtractor` | `JsoupLinkExtractor` | sitemap reader |
| `CrawlScope` | `SameHostScope` | robots.txt + several hosts |
| `CrawlListener` | `ConsoleCrawlListener` | JSON or database writer |

`CrawlRunner` is the only class that constructs the live implementations. `Crawler` never mentions HTTP, Jsoup, or `System.out`.

## Design decisions

### Same host, not same origin

The brief says: crawl that domain only, not other domains or subdomains.

- `example.com` is allowed
- `www.example.com` and `blog.example.com` are not
- `http` vs `https`, and a different port, are still the same host, so they are allowed

That is a strict hostname match after canonicalisation. Matching the registered domain (`example.com` and `www.example.com`) would need extra policy and a public-suffix list. I kept the strict reading.

### Print every HTTP link, fetch only in-scope ones

The brief asks for every URL found on the page. External and subdomain links are therefore printed, then dropped by `CrawlScope` before `Frontier.offer`. That split lives in `Crawler.crawlDiscoveredLinks`.

### Canonical URLs

`UrlNormalizer` is the only place URLs are rewritten. It:

- lowercases scheme and host
- drops default ports and fragments
- treats `http://host` and `http://host/` as the same page
- resolves `.` / `..`
- encodes illegal characters
- drops `user:password@` so credentials are never printed or sent

It keeps path case, trailing slashes, and query strings, because servers may treat those as different resources.

`java.net.URI.getHost()` returns empty for names such as `sub.127.0.0.1` (the Zego harness uses this form). The last labels look like a broken IPv4 address. Browsers still treat it as a hostname, so the normaliser falls back to the raw authority. Without that, subdomain links would be silently dropped and the harness would fail.

### Redirects are followed in the fetcher, hop by hop

The `HttpClient` is built with `Redirect.NEVER`. `HttpPageFetcher` follows 301/302/303/307/308 itself and checks `CrawlScope` before requesting the next hop. An off-host `Location` is a skip, not a fetch. Automatic redirects would leak requests to other hosts.

### Completion uses unfinished work, not an empty queue

`unfinishedTasks` counts queued work plus in-flight fetches. A worker that sees an empty queue must not exit if another worker is still fetching a page that may discover more links. Children are accepted *before* the parent is marked done, so the counter cannot hit zero early.

Workers are virtual threads. Crawling is wait-on-network work; virtual threads keep the code blocking and readable. `concurrency` is the politeness and resource limit.

### Page outcomes are a sealed type

`FetchResult` is `Fetched`, `Skipped`, or `Failed`. A 404 or a PDF is a skip, not a failed crawl. The process exits 0 after a completed run. One bad page does not stop the others.

### Limits

`HttpFetcherConfig` sets timeout, redirect cap, body size, and User-Agent. The body is rejected from `Content-Length` when possible, otherwise by reading at most `max + 1` bytes. `Accept-Encoding: identity` avoids gzip bombs and Java’s lack of automatic decompression.

## Alternatives considered

| Option | Why not |
| --- | --- |
| Scrapy / crawler4j / Playwright | Forbidden by the brief; too much framework for the design to show |
| `CompletableFuture` / reactive HTTP | Harder to read; virtual threads already give concurrency |
| Fixed OS thread pool | Fine, but heavier for I/O-bound work |
| Jsoup’s own HTTP fetch | Would mix parsing and I/O and make fakes harder |
| Strip trailing slashes always | `/page` and `/page/` can be different resources |
| Count non-HTML as failure | A PDF on a normal site should not fail the process |

## Trade-offs and time limits

Built now:

- exact-host scope
- concurrent workers
- redirect scope checks
- size, depth, and timeout limits
- fat jar + wrapper script
- unit, fake-HTTP, and harness checks

Described, not built:

- `robots.txt` and per-host delay
- retries with jitter and `Retry-After`
- a page-count cap in the crawler (the frontier already has depth)
- persisting the frontier so a crawl can resume
- treating `www` and apex as the same site, behind a flag

## How I would extend it

**Several domains at once.** `CrawlScope` becomes a set of hosts. The frontier gains one queue per host so each site can be rate-limited. Workers stay the same.

**Why a CLI is not enough for that.** A large multi-domain crawl is a long-running job. You want start/cancel, progress, several users, and stored results. I would expose `POST /crawls` and `GET /crawls/{id}` and run the same `Crawler` inside the service.

**Several machines.** Replace `InMemoryFrontier` with Redis (`SADD` for seen URLs, a list or stream for the queue) or Kafka. Workers stay stateless. Partition by host so politeness stays per site.

**Retries and politeness.** Decorate `PageFetcher`: `new RetryingFetcher(new RateLimitedFetcher(httpFetcher))`. No change to `Crawler`.

**SSRF, if users can submit URLs.** Resolve the host and block private / link-local / metadata addresses, including after redirects. Not required for a local CLI.

**JavaScript-rendered pages.** Out of scope for this brief. It would be another `PageFetcher` using a headless browser.

## Testing

| Area | What is covered |
| --- | --- |
| `UrlNormalizer` | fragments, ports, relative links, encoding, `sub.127.0.0.1` |
| `SameHostScope` | subdomains, lookalike hosts, scheme/port differences |
| `JsoupLinkExtractor` | relative links, `<base>`, entities, malformed HTML |
| `HttpPageFetcher` | charset, 404, PDF, size cap, in-scope redirect, out-of-scope redirect, timeout |
| `InMemoryFrontier` | first-seen, depth, two threads offering the same URL |
| `Crawler` | cycles, external links, failed pages, depth, concurrency cap |
| `CrawlCommand` | defaults, flags, `--help` |

Verified outside the unit tests:

- `java -jar build/libs/crawler.jar https://example.com` — fetched 1 page in 0.33s. The current example.com homepage has no `<a href>` links.
- Zego’s language-agnostic harness (evaluation PR #26): **11/11 passed**, including “print subdomain URLs but do not fetch them” and “no duplicate fetches”.

## Project layout

```text
java/
  src/main/java/com/hamzaali/crawler/
    Main.java
    cli/          argument parsing and wiring
    core/         Crawler coordinator
    fetch/        HTTP
    frontier/     queue + seen set
    output/       printing
    parse/        HTML links
    url/          canonicalisation + scope
  src/test/java/  JUnit 5 tests
  run_crawler.sh  build if needed, then run the jar
```
