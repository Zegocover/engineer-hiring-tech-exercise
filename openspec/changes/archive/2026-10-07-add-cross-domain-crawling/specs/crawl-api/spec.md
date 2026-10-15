# Spec Delta

## MODIFIED Requirements

### Requirement: Clients can start a crawl
The service SHALL accept a request to crawl a base URL with optional limits: page budget, depth, concurrency, per-host concurrency, robots.txt handling, and a list of additional allowed host patterns. It SHALL start the crawl in the background and respond immediately with status 202, the new crawl's identifier, its initial state and a `Location` header pointing at the crawl.

#### Scenario: Start a crawl
- **WHEN** a client sends `POST /crawls` with `{"url": "https://example.com/"}`
- **THEN** the response is 202 with a unique `id`, `status` of `running` and a `Location` of `/crawls/{id}`, and the crawl proceeds without the client waiting

#### Scenario: Start a cross-domain crawl
- **WHEN** a client sends `POST /crawls` with `{"url": "https://example.com/", "allowed_hosts": ["*.example.com", "docs.partner.io"], "per_host_concurrency": 2}`
- **THEN** the response is 202, and the crawl follows links into those hosts with at most 2 requests per host at a time

### Requirement: Clients can read a crawl's details
The service SHALL return, at `GET /crawls/{id}`, a known crawl's identifier, base URL, effective limits (including allowed host patterns and per-host concurrency), status (`running`, `completed`, `failed` or `cancelled`), start and finish times, statistics and error message, if any. An unknown identifier SHALL return 404.

#### Scenario: Details include effective limits
- **WHEN** a client starts a crawl with `max_depth` 2 and no other limits, then requests `GET /crawls/{id}`
- **THEN** the response shows `max_depth` 2, the service's default page budget and concurrency, an empty `allowed_hosts` list and no per-host concurrency limit

#### Scenario: Details include allowed hosts
- **WHEN** a client starts a crawl with `allowed_hosts` `["*.example.com"]`, then requests `GET /crawls/{id}`
- **THEN** the response's limits show `allowed_hosts` `["*.example.com"]`

#### Scenario: Unknown crawl
- **WHEN** a client requests `GET /crawls/{id}` with an identifier the service has never issued
- **THEN** the response is 404

### Requirement: Crawls follow the site-crawl rules
Each crawl started through the service SHALL follow the same crawl rules as the command-line crawl. It SHALL stay within the crawl scope (the base URL's host plus any allowed host patterns), fetch each normalised URL at most once, report normalised links, and respect each host's robots.txt unless the request disables it.

#### Scenario: Off-host links reported but not fetched
- **WHEN** a crawled page links to `https://other.org/` and `other.org` is not allowed
- **THEN** that link appears in the page's reported links, and no page for `https://other.org/` appears in the crawl's results

#### Scenario: Allowed host's pages appear in results
- **WHEN** a crawl allows `docs.partner.io` and a crawled page links to `https://docs.partner.io/guide`
- **THEN** a page for `https://docs.partner.io/guide` appears in the crawl's results

## ADDED Requirements

### Requirement: Allowed host patterns are validated and bounded
The service SHALL reject a crawl request with status 422, and create no crawl, when any allowed host pattern is not a valid host or `*.`-prefixed domain, or when more patterns are given than the service allows (50).

#### Scenario: Invalid pattern
- **WHEN** a client sends `allowed_hosts` `["https://example.com/path"]` or `["exa*mple.com"]`
- **THEN** the response is 422 naming the invalid pattern, and no crawl is created

#### Scenario: Too many patterns
- **WHEN** a client sends 51 allowed host patterns
- **THEN** the response is 422 and no crawl is created
