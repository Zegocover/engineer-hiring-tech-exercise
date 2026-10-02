# robots.txt implementation plan

Fetch `/robots.txt` once at the beginning of a crawl, parse its rules, and check
each page URL against those stored rules before fetching it. Do not fetch a
robots file for every page. Fetch another file only if the origin changes.

An origin consists of the scheme, hostname, and port. The seed hostname remains
the crawl boundary, even when another scheme or port is encountered.

## Implementation

1. Set the crawler identity to `ExerciseCrawler` and send
   `User-Agent: ExerciseCrawler/1.0` on HTTP requests.
2. Add `internal/robots` with an `Allowed(ctx, URL) (bool, error)` operation.
   Load the seed origin's rules before fetching the seed page. Cache parsed rules
   and retrieval outcomes per origin for the duration of the crawl. Evaluate an
   existing parser before implementing a custom one.
3. Support user-agent selection, `Allow`, `Disallow`, wildcard matching, and
   longest-match precedence. Follow [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)
   for rule evaluation and retrieval behavior.
4. Apply the following retrieval policy: allow crawling after a 4xx response;
   block the affected origin after a 5xx response or network failure; propagate
   context errors. Retain usable rules when individual lines cannot be parsed.
   Bound retrieval time and response size.
5. Check the seed and every internal page before making its HTTP request.
   Report disallowed URLs without fetching them. Do not load robots rules for
   external hosts, since those URLs are only reported.
6. Validate redirect destinations before fetching them: enforce the seed
   hostname boundary and check the destination origin's rules. Use a separate
   robots retrieval path so fetching rules does not recursively trigger another
   robots check. Bound redirect hops and resolve page links against the final
   response URL. Keep robots redirects inside the seed hostname, documenting
   this exercise-specific restriction relative to RFC 9309's cross-authority
   redirect guidance. Treat a blocked robots redirect as a retrieval failure
   and block that origin for the crawl.

## Tests

- Use table-driven tests with named `t.Run` subtests and local HTTP handlers.
- Cover allowed paths, blocked paths, specific allow exceptions, user-agent
  selection, wildcard rules, and longest-match precedence.
- Cover missing robots files, server errors, network failures, and malformed
  rules.
- Verify cache reuse across pages and separate rule retrieval for different
  origins.
- Verify blocked seeds and redirect destinations are never fetched.
- Add `cmd/cli/testdata/robots/site/` with `robots.txt`, `index.html`,
  `public.html`, and `private.html`. Link to both pages from the index and
  disallow the private page. Call `Run()` using the existing file-server test
  pattern and an expected-output fixture. Count requests to verify that both
  links are reported, the public page is fetched, the private page receives no
  requests, and `/robots.txt` is fetched once.

## Completion

Document the user-agent, failure policy, cache lifetime, and redirect restriction
in the design notes. Run `go test ./...` and resolve failures related to the change.

Keep the first version's cache scoped to one crawl. Leave `Crawl-delay`, sitemap
traversal, persistent caching, and worker concurrency for later work.
