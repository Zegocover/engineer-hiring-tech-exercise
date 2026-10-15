# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Only the exact crawl host is followed`
- TO: `### Requirement: Only in-scope hosts are followed`

- FROM: `### Requirement: Redirects leaving the host are not followed`
- TO: `### Requirement: Redirects leaving the crawl scope are not followed`

## MODIFIED Requirements

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

### Requirement: Redirects leaving the crawl scope are not followed
The system SHALL NOT parse or report a page whose final URL, after redirects, is outside the crawl scope. A redirect to another in-scope host SHALL be followed and reported under its final URL.

#### Scenario: Off-host redirect
- **WHEN** `https://example.com/go` redirects to `https://other.org/` and `other.org` is not in scope
- **THEN** no page is reported for that fetch and no links from `other.org` are queued

#### Scenario: Redirect to an allowed host
- **WHEN** the user allows `www.example.com` and `https://example.com/` redirects to `https://www.example.com/`
- **THEN** the page is reported as `https://www.example.com/` and its links are followed

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
