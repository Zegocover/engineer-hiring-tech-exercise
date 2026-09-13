# Crawler design

| Step | TODO | Description |
| --- | --- | --- |
| 1 | Simple crawler that gets only first links | Fetch the seed page, parse anchor links, resolve relative URLs, and print the page URL with its discovered links. Do not traverse yet. |
| 2 | Filter by first link domain | Treat the seed URL as the hostname boundary. Only schedule HTTP(S) URLs with that exact hostname; report external links without fetching them. |
| 3 | Elaborate crawler that loops through the links | Maintain a queue of discovered URLs. Continue fetching eligible pages until no pending or in-flight work remains. |
| 4 | Deduplicate URLs | Remove fragments and track scheduled URLs in a coordinator-owned set. Mark URLs before enqueueing to prevent duplicate work and cycles. |
| 5 | Follow redirects | Validate every redirect destination against the seed hostname before fetching it. Limit redirect hops and resolve discovered links against the final response URL. |
| 6 | Respect robots.txt | Load and cache robots rules per origin for the crawler user agent. Check rules before page requests, including redirect destinations. Define retrieval-failure handling during implementation. |
| 7 | Rate limiter | Share a context-aware request limiter across all fetches, including robots retrieval and redirect hops. Configure request rate and burst size. |
| 8 | Multiple workers | Use a fixed worker pool to fetch pages concurrently. Workers return results to the coordinator. |
