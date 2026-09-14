# Crawler design

| Step | TODO | Description |
| --- | --- | --- |
| 1 | Simple crawler that gets only first links | Fetch the seed page, parse anchor links, resolve relative URLs, and print the page URL with its discovered links. Do not traverse yet. |
| 2 | Filter by first link domain | Treat the seed URL as the hostname boundary. Only schedule HTTP(S) URLs with that exact hostname; report external links without fetching them. |
| 3 | Elaborate crawler that loops through the links | Maintain a queue of discovered URLs. Continue fetching eligible pages until no pending or in-flight work remains. |
| 4 | Deduplicate URLs | Remove fragments and track scheduled URLs in a coordinator-owned set. Mark URLs before enqueueing to prevent duplicate work and cycles. |
| 5 | Respect robots.txt | Load and cache robots rules per origin for the crawler user agent. Check rules before page requests, including redirect destinations. Define retrieval-failure handling during implementation. |
| 6 | Multiple workers | Use a fixed worker pool to fetch pages concurrently. Workers return results to the coordinator. |

## Basic robots.txt support

The crawler fetches `/robots.txt` before the first page request and caches its
seed origin's rules for one crawl. Separate policies for other schemes or ports
are not implemented yet.
Rules are parsed and matched by `github.com/temoto/robotstxt` v1.1.2 through
`internal/robots`; the HTTP client handles retrieval.

Rules are selected for `ExerciseCrawler`, and requests identify as
`ExerciseCrawler/1.0`. Allow/disallow matching, including wildcard paths and
end anchors, follows the module's behavior. Its equal-length rule precedence
can depend on rule order, so this is not claimed as full RFC 9309 compliance.

Blocked URLs are reported without fetching them. A 4xx robots response allows
crawling; network failures, parser errors, and other unsuccessful responses
stop the crawl or deny access when parsing fails. Malformed lines tolerated by
the module do not prevent using its parsed rules. Context errors during robots
retrieval propagate to the caller; cancellation during crawling returns partial
results with a nil error. No overall HTTP request timeout is configured;
requests use the caller’s context.

The HTTP client rejects all redirects. Page redirects are reported as HTTP
errors; a robots.txt redirect stops the crawl as a retrieval failure.
`Crawl-delay` and sitemaps are not acted on. Response-size limits and concurrent
cache access remain future work.

## Concurrency approach

I chose a fixed worker pool because HTTP requests are the slowest part of the crawl. Workers fetch pages and extract links concurrently, while a single coordinator owns the queue, tracks scheduled URLs, and collects results. This avoids explicit mutex protection for shared crawl state, although channels still provide synchronization. The worker count bounds concurrent requests, but queue and result memory can grow. An alternative is a mutex-protected queue with a separate result collector; a ring buffer is one possible queue implementation.
