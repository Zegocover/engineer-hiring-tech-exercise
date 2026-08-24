# Go Single-Domain Crawler

## Usage

From this directory, run:

```text
go run ./cmd/crawler -startUrl https://example.com -workers 4 -log_level info
```

The crawler writes `output.txt` in the current working directory, with one normalized URL per line. `-workers` defaults to `1`. `-startUrl` is required, must be an absolute HTTP(S) URL, and `-workers` must be at least `1`. `-log_level` defaults to `info` and accepts `error`, `info`, or `debug`.

Logs are written to stderr. `error` reports every crawl, validation, and output error. `info` also reports when scraping starts, when output-file creation starts, and the number of URLs scraped after completion. `debug` additionally reports each URL a worker processes or discards.

## Design

The seed hostname is the crawl boundary. Links are resolved against the page URL, fragments are removed, and only HTTP(S) links whose exact hostname matches the seed are scheduled. This excludes subdomains. Query strings are retained because they can identify different resources. Same-host redirects are followed; redirects outside the target host fail that page without making an external request.

The request channel has a fixed capacity of 1000. A coordinator owns the queue and schedules URLs while receiving worker results in the same `select` loop. This prevents a page containing more than 1000 links from blocking all workers: excess links remain in the coordinator's queue. The coordinator also owns URL deduplication, and tracks dispatched URLs until their results arrive. Crawling is complete when there are no queued URLs and no URLs still being processed. Child failures are logged and do not stop the crawl. A seed failure is returned immediately after the workers shut down.

Workers select between incoming requests and context cancellation. HTTP requests have a 15-second timeout and transient failures are retried up to three total attempts with a short backoff. HTTP 429, 500, 502, 503, and 504 responses are considered retryable. HTML parsing is limited to 2 MiB per response. Non-success responses and non-HTML responses are not parsed. Robots.txt, rate limiting, and maximum-page controls are intentionally outside this exercise's CLI contract.

## Dependency choice

HTTP, URL resolution, concurrency, flags, and file output use the Go standard library. Go does not provide an HTML parser in its standard library, so `golang.org/x/net/html` is used for tolerant HTML parsing. A hand-written parser was rejected because it would be less accurate for malformed real-world HTML.

## AI usage
Everything written above is AI, everything below is typed.
I used the free version of copilot to plan and implement this project.
In my job I normally use claude code, but I don't have it personally.

## Design decisions
The scope of this project is intentionally very small. I have omitted many superfluous features of a web crawler. This just looks for links, then retrieves the links, discarding any not in the target domain. We don't look at any robots.txt or check headers for rate limits.
As a slight extension to the basic requirements, I added logging for observability; a simple retrier for resilience and a timer for simple benchmarking.

The primary design decision was the method to parallelize the fetching of urls.
Go's channels were a natural candidate for providing the URLs to the workers, but are bounded. I arbitrarily selected a size of 1000. To prevent deadlocking, the main thread would handle deduplicating & enqueueing new urls, while worker goroutines would listen for urls to process & return the results.

## Scaling up for production
If I had to scale up the system for production, I would have the workers be lambda functions which pull from an SQS queue.
To store the urls, I would use a database. The exact database would depends on what we intend to do with the gathered data and its structure.

## Testing
We have some small unit tests to ensure small functions are working as designed.
I performed live tests using https://books.toscrape.com/ with the following results:

URLs scraped: 1195

| Workers | Scrape time |
|--------:|-------------|
| 1       | 1m58s       |
| 2       | 1m1s        |
| 5       | 26.5s       |
| 10      | 15.6s       |
| 50      | 7.5s        |
| 100     | 6.4s        |