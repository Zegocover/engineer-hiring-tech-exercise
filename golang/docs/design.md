# Crawler design

| Step | TODO | Description |
| --- | --- | --- |
| 1 | Simple crawler that gets only first links | Fetch the seed page, parse anchor links, resolve relative URLs, and print the page URL with its discovered links. Do not traverse yet. |
| 2 | Filter by first link domain | Treat the seed URL as the hostname boundary. Only schedule HTTP(S) URLs with that exact hostname; report external links without fetching them. |
| 3 | Elaborate crawler that loops through the links | Maintain a queue of discovered URLs. Continue fetching eligible pages until no pending or in-flight work remains. |
| 4 | Deduplicate URLs | Remove fragments and track scheduled URLs in a coordinator-owned set. Mark URLs before enqueueing to prevent duplicate work and cycles. |
| 6 | Respect robots.txt | Load and cache robots rules per origin for the crawler user agent. Check rules before page requests, including redirect destinations. Define retrieval-failure handling during implementation. |
| 7 | Rate limiter | Share a context-aware request limiter across all fetches, including robots retrieval and redirect hops. Configure request rate and burst size. |
| 8 | Multiple workers | Use a fixed worker pool to fetch pages concurrently. Workers return results to the coordinator. |

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
stop the crawl or deny access when parsing fails. Malformed lines tolerated by the module do not prevent using
its parsed rules. Context errors propagate to the caller. HTTP requests have a
ten-second timeout.

Redirects remain disabled until destination checks are implemented: a page
redirect returns an HTTP error and a robots redirect blocks its origin.
`Crawl-delay` and sitemaps are not acted on. Response-size limits and concurrent
cache access remain future work.

The file-server integration fixture under `cmd/cli/testdata/robots` checks that
rules are fetched once, allowed pages are fetched, and blocked pages receive
zero requests while remaining in output.
