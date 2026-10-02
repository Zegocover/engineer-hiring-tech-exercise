# golang-developer-test

## Running the Go implementation

Run these commands from the `golang` directory using the Go version declared in
`go.mod` (currently 1.27.1):

```sh
go run ./cmd/cli https://example.com/
go test ./...
go test -race ./...
```

The CLI accepts a seed URL as its first argument. It prints a flat list of unique
URLs after the crawl completes; ordering is unspecified. JSON logs currently
share standard output with the URL list. Ctrl+C cancels HTTP requests through
the crawl context.

## Requirements

- Accept an HTTP(S) seed URL through a Go CLI.
- Print each page URL and its discovered links.
- Crawl only the seed hostname.
- Resolve relative links, deduplicate URLs, and respect robots.txt.
- Use bounded concurrency, reuse connections, and support cancellation.
- Test with local HTTP fixtures and race detection.
- Document design trade-offs, limitations, and development tools.

## Out of scope

- Rate limiting: Cap the number of requests per second.
- Robots crawl delay: Honor the `Crawl-delay` directive in robots.txt.
- Multiple domains: Crawl more than one seed hostname.
- OTEL support

## Design decisions and trade-offs

I chose a fixed pool of four workers to fetch pages and extract links concurrently,
since HTTP requests are the slowest part of the crawl. A single coordinator owns
the queue, deduplication set, and results, using channels to distribute work and
collect responses. URLs are marked when scheduled to prevent duplicate requests
and cycles. This keeps shared state simple and bounds concurrency, though channels
still involve synchronization and the queue can grow with the site.

## Development and AI tooling

Development combined manual work with AI assistance through Codex with Astra.
I used Codex for research, design discussions, code review, and selected
implementation tasks, then reviewed and refined the generated code. Verification
used Go tests, race detection, and local HTTP fixtures.
