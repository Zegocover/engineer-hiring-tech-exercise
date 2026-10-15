# site-crawl Specification

## Purpose

Crawl every reachable page on a single host, starting from a base URL, and report each visited page together with all the URLs found on it.

## Requirements

### Requirement: Crawl starts from a base URL
The system SHALL accept a single absolute `http` or `https` base URL, fetch it first, and treat its host as the crawl scope. A base URL that is not absolute or not `http(s)` SHALL be rejected before any request is made.

#### Scenario: Valid base URL
- **WHEN** the user starts a crawl with `https://example.com/`
- **THEN** the system fetches `https://example.com/` and treats `example.com` as the crawl host

#### Scenario: Invalid base URL
- **WHEN** the user starts a crawl with `example.com` or `ftp://example.com/`
- **THEN** the system exits with a non-zero status and an error message, and makes no request

### Requirement: Only in-scope hosts are followed
The system SHALL follow links only when their host is in the crawl scope. The scope is the crawl host plus any host patterns the user allows. Host matching SHALL be case-insensitive and ignore default ports. With no allowed patterns, only the exact crawl host is in scope. Links to hosts outside the scope, including `www.` variants and subdomains not allowed, SHALL be reported but not fetched.

#### Scenario: Same-host link is followed
- **WHEN** a page on `example.com` links to `https://example.com/about`
- **THEN** `https://example.com/about` is fetched

#### Scenario: Subdomain link is not followed
- **WHEN** a page on `example.com` links to `https://blog.example.com/` or `https://www.example.com/` and no host patterns are allowed
- **THEN** the link appears in that page's reported links and is not fetched

#### Scenario: External link is not followed
- **WHEN** a page links to `https://other.org/` and `other.org` is not allowed
- **THEN** the link appears in that page's reported links and is not fetched

#### Scenario: Allowed exact host is followed
- **WHEN** the user allows `docs.partner.io` and a page on `example.com` links to `https://docs.partner.io/guide`
- **THEN** `https://docs.partner.io/guide` is fetched, and links found on it are followed under the same scope

#### Scenario: Subdomain wildcard
- **WHEN** the user allows `*.example.com` and pages link to `https://blog.example.com/`, `https://a.b.example.com/` and `https://example.org/`
- **THEN** the two `example.com` subdomains are fetched and `https://example.org/` is only reported

### Requirement: Each visited page is reported with all its links
For every page successfully fetched and parsed as HTML, the system SHALL report the page URL followed by every link found on that page, in document order with duplicates on the same page removed.

#### Scenario: Page with mixed links
- **WHEN** a page contains links to `/a`, `/a`, `https://other.org/` and `/b`
- **THEN** the page is reported with links `https://example.com/a`, `https://other.org/`, `https://example.com/b`

#### Scenario: Page with no links
- **WHEN** a fetched HTML page contains no links
- **THEN** the page is still reported, with an empty link list

### Requirement: Links are resolved and normalised
The system SHALL resolve each link against the page's final URL after redirects, honouring a `<base href>` element. Fragments SHALL be removed, scheme and host lowercased, and default ports dropped. Links with non-HTTP schemes (`mailto:`, `tel:`, `javascript:`, etc.) SHALL be ignored.

#### Scenario: Relative link after redirect
- **WHEN** `https://example.com/old` redirects to `https://example.com/new/` and that page links to `page`
- **THEN** the reported link is `https://example.com/new/page`

#### Scenario: Fragment and case normalisation
- **WHEN** a page links to `HTTPS://Example.COM:443/x#section`
- **THEN** the reported link is `https://example.com/x`

#### Scenario: Non-HTTP link
- **WHEN** a page links to `mailto:hi@example.com`
- **THEN** the link is neither reported nor fetched

### Requirement: Each page is fetched at most once
The system SHALL fetch each normalised URL at most once per crawl, regardless of how many pages link to it or how many concurrent workers are running.

#### Scenario: Cyclic links
- **WHEN** page A links to B and B links back to A
- **THEN** A and B are each fetched exactly once and the crawl terminates

### Requirement: Only HTML responses are parsed
The system SHALL parse links only from successful responses whose content type is HTML. Other successful responses SHALL NOT be reported as pages.

#### Scenario: Non-HTML resource
- **WHEN** a same-host link points to a PDF or image
- **THEN** it is fetched at most once, no links are extracted from it, and it is not reported as a page

### Requirement: Redirects leaving the crawl scope are not followed
The system SHALL NOT parse or report a page whose final URL, after redirects, is outside the crawl scope. A redirect to another in-scope host SHALL be followed and reported under its final URL.

#### Scenario: Off-host redirect
- **WHEN** `https://example.com/go` redirects to `https://other.org/` and `other.org` is not in scope
- **THEN** no page is reported for that fetch and no links from `other.org` are queued

#### Scenario: Redirect to an allowed host
- **WHEN** the user allows `www.example.com` and `https://example.com/` redirects to `https://www.example.com/`
- **THEN** the page is reported as `https://www.example.com/` and its links are followed

### Requirement: Failures do not stop the crawl
A request that fails (timeout, connection error, HTTP error status) SHALL be retried a bounded number of times for transient failures (timeouts, connection errors, 429, 5xx). It SHALL then be recorded as an error, and the crawl SHALL continue with the remaining pages.

#### Scenario: One page returns 500
- **WHEN** one page consistently returns HTTP 500 and others succeed
- **THEN** the other pages are crawled and reported, and the failed URL is counted as an error in the summary

#### Scenario: Transient failure recovers
- **WHEN** a page returns HTTP 503 once and then 200
- **THEN** the page is reported normally

### Requirement: Crawl terminates when no work remains
The system SHALL finish when every queued URL has been processed, and SHALL exit with status 0 when the base URL was fetched successfully, even if other pages failed.

#### Scenario: Normal completion
- **WHEN** all reachable same-host pages have been processed
- **THEN** the command exits with status 0 and prints a summary of pages crawled and errors

#### Scenario: Base URL unreachable
- **WHEN** the base URL cannot be fetched after retries
- **THEN** the command exits with a non-zero status

### Requirement: Crawl limits are configurable
The system SHALL support limiting concurrency, total pages fetched and link depth from the base URL, plus a per-request timeout. It SHALL also support an optional per-host concurrency limit that caps simultaneous requests to any one host within the overall concurrency; with none set, any one host may use all the concurrency. When a page or depth limit is reached, no further URLs beyond it SHALL be fetched.

#### Scenario: Page limit
- **WHEN** the user sets a maximum of 10 pages on a site with 100 pages
- **THEN** no more than 10 pages are fetched

#### Scenario: Depth limit
- **WHEN** the user sets maximum depth 1
- **THEN** only the base URL and pages it links to directly are fetched

#### Scenario: Per-host concurrency limit
- **WHEN** the user sets concurrency 8 and a per-host limit of 2, and the crawl reaches two hosts with many pages each
- **THEN** at no point are more than 2 requests to the same host in flight

### Requirement: robots.txt is respected by default
The system SHALL read `robots.txt` separately for each host the crawl reaches, before fetching any other URL from that host, and skip that host's disallowed URLs unless the user disables this behaviour. Each host's `robots.txt` SHALL be fetched at most once per crawl. Skipped URLs SHALL still appear in the reported links of pages that link to them, and SHALL NOT count against the page limit.

#### Scenario: Disallowed path
- **WHEN** `robots.txt` disallows `/private/` and a page links to `/private/x`
- **THEN** `/private/x` is reported as a link but not fetched

#### Scenario: robots.txt disabled
- **WHEN** the user disables robots handling
- **THEN** `/private/x` is fetched

#### Scenario: Each allowed host's own robots.txt applies
- **WHEN** the user allows `docs.partner.io`, whose `robots.txt` disallows `/drafts/`, while the crawl host's `robots.txt` does not
- **THEN** `https://docs.partner.io/drafts/x` is not fetched, the same path on the crawl host is fetched, and each host's `robots.txt` is requested once

### Requirement: Output formats
The command SHALL write results to standard output as human-readable text by default, or as one JSON object per page per line (`{"url": ..., "links": [...]}`) when JSON Lines output is selected. Diagnostics and the summary SHALL go to standard error. Output for one page SHALL never interleave with another's.

#### Scenario: Text output
- **WHEN** the crawl runs with default output
- **THEN** each page appears as its URL followed by its links, one per indented line

#### Scenario: JSON Lines output
- **WHEN** the crawl runs with JSON Lines output
- **THEN** every stdout line parses as a JSON object with `url` and `links` keys
