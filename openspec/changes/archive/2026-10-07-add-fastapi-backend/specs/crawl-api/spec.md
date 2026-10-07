# Spec Delta

## Purpose

Lets clients run site crawls over HTTP: start several crawls in one service, follow their progress, read the pages they find and cancel them, without blocking on a crawl to finish.

## ADDED Requirements

### Requirement: Clients can start a crawl
The service SHALL accept a request to crawl a base URL with optional limits (page budget, depth, concurrency, robots.txt handling). It SHALL start the crawl in the background and respond immediately with status 202, the new crawl's identifier, its initial state and a `Location` header pointing at the crawl.

#### Scenario: Start a crawl
- **WHEN** a client sends `POST /crawls` with `{"url": "https://example.com/"}`
- **THEN** the response is 202 with a unique `id`, `status` of `running` and a `Location` of `/crawls/{id}`, and the crawl proceeds without the client waiting

### Requirement: Invalid crawl requests are rejected
The service SHALL reject a crawl request whose URL is not an absolute `http` or `https` URL, or whose limits are out of range, with status 422 and a description of the problem. No crawl SHALL be created for a rejected request.

#### Scenario: Non-HTTP URL
- **WHEN** a client sends `POST /crawls` with `{"url": "ftp://example.com/"}`
- **THEN** the response is 422 and `GET /crawls` does not list a new crawl

#### Scenario: Negative depth
- **WHEN** a client sends `POST /crawls` with a `max_depth` of `-1`
- **THEN** the response is 422

### Requirement: Server limits bound every crawl
The service SHALL apply a default page budget when a request does not set one, and SHALL reject requests whose page budget or concurrency exceed the service's configured maxima with status 422.

#### Scenario: Default page budget applied
- **WHEN** a client starts a crawl without `max_pages`
- **THEN** the crawl's reported limits show the service's default page budget, and it fetches no more pages than that budget

#### Scenario: Page budget above the maximum
- **WHEN** a client requests a `max_pages` greater than the service's configured maximum
- **THEN** the response is 422 and no crawl is created

### Requirement: Clients can read a crawl's details
The service SHALL return, at `GET /crawls/{id}`, a known crawl's identifier, base URL, effective limits, status (`running`, `completed`, `failed` or `cancelled`), start and finish times, statistics and error message, if any. An unknown identifier SHALL return 404.

#### Scenario: Details include effective limits
- **WHEN** a client starts a crawl with `max_depth` 2 and no other limits, then requests `GET /crawls/{id}`
- **THEN** the response shows `max_depth` 2 and the service's default page budget and concurrency

#### Scenario: Unknown crawl
- **WHEN** a client requests `GET /crawls/{id}` with an identifier the service has never issued
- **THEN** the response is 404

### Requirement: Clients can poll a crawl's status
The service SHALL provide `GET /crawls/{id}/status`, a lightweight response for polling, with the crawl's status, start and finish times, error message if any, and running statistics: pages reported, URLs fetched, errors and URLs skipped by robots.txt. It SHALL omit the crawl's limits and results. An unknown identifier SHALL return 404.

#### Scenario: Status while running
- **WHEN** a client requests `GET /crawls/{id}/status` for a crawl still in progress
- **THEN** the response has `status` `running`, no finish time, and statistics reflecting the pages reported so far

#### Scenario: Status after completion
- **WHEN** a crawl of a three-page site with one failing page finishes and a client requests `GET /crawls/{id}/status`
- **THEN** the response has `status` `completed`, a finish time, 2 pages and 1 error

#### Scenario: Status of an unknown crawl
- **WHEN** a client requests `GET /crawls/{id}/status` with an identifier the service has never issued
- **THEN** the response is 404

### Requirement: Clients can page through a crawl's results
The service SHALL return a crawl's pages, each with its URL and its links in document order, in the order the crawl reported them, using `offset` and `limit` query parameters, along with the total number of pages so far. Results SHALL be readable while the crawl is still running. An unknown identifier SHALL return 404.

#### Scenario: Read results in pages
- **WHEN** a crawl has reported 5 pages and a client requests `GET /crawls/{id}/pages?offset=2&limit=2`
- **THEN** the response contains the third and fourth reported pages and a total of 5

#### Scenario: Read results while running
- **WHEN** a client requests the pages of a crawl that is still running
- **THEN** the response contains the pages reported so far

### Requirement: Clients can list the links a crawl found
The service SHALL provide `GET /crawls/{id}/links`, returning every distinct normalised link found on any of the crawl's reported pages, in the order each was first found, using `offset` and `limit` query parameters, with the total number of distinct links so far. It SHALL include links that were not followed (other hosts, disallowed by robots.txt, beyond limits). Links SHALL be readable while the crawl is still running. An unknown identifier SHALL return 404.

#### Scenario: Links de-duplicated across pages
- **WHEN** the home page links to `/a` and `/b`, and `/a` links to `/b` and `/c`
- **THEN** `GET /crawls/{id}/links` returns `/a`, `/b` and `/c` (as absolute URLs) once each, in that order, with a total of 3

#### Scenario: Links not followed are listed
- **WHEN** a crawled page links to `https://other.org/`
- **THEN** `https://other.org/` appears in the crawl's links

#### Scenario: Read links in pages
- **WHEN** a crawl has found 5 distinct links and a client requests `GET /crawls/{id}/links?offset=1&limit=2`
- **THEN** the response contains the second and third links found and a total of 5

#### Scenario: Links of an unknown crawl
- **WHEN** a client requests `GET /crawls/{id}/links` with an identifier the service has never issued
- **THEN** the response is 404

### Requirement: Clients can list crawls
The service SHALL list every crawl it holds with its identifier, base URL, status and statistics, most recently started first.

#### Scenario: Two crawls listed
- **WHEN** a client starts a crawl of `https://a.example/` and then one of `https://b.example/`, then requests `GET /crawls`
- **THEN** both crawls are listed, with the `https://b.example/` crawl first

### Requirement: Crawls follow the site-crawl rules
Each crawl started through the service SHALL follow the same crawl rules as the command-line crawl: it SHALL stay on the base URL's host, fetch each normalised URL at most once, report normalised links and respect robots.txt unless the request disables it.

#### Scenario: Off-host links reported but not fetched
- **WHEN** a crawled page links to `https://other.org/`
- **THEN** that link appears in the page's reported links, and no page for `https://other.org/` appears in the crawl's results

### Requirement: Crawls run concurrently and independently
The service SHALL run several crawls at the same time. A crawl's results, statistics, failure or cancellation SHALL NOT affect any other crawl.

#### Scenario: Cancelling one crawl leaves another running
- **WHEN** two crawls are running and a client cancels the first
- **THEN** the second keeps running and later reaches `completed` with its own results

### Requirement: Clients can cancel a running crawl
The service SHALL let a client cancel a running crawl with `DELETE /crawls/{id}`. The crawl SHALL stop fetching, end with status `cancelled` and keep the pages it had already reported. Cancelling a crawl that has already finished SHALL return 409 and leave its status unchanged. An unknown identifier SHALL return 404.

#### Scenario: Cancel a running crawl
- **WHEN** a client cancels a crawl that has reported 3 pages and is still running
- **THEN** the crawl's status becomes `cancelled`, it fetches no further URLs, and its results still contain the 3 pages

#### Scenario: Cancel a finished crawl
- **WHEN** a client cancels a crawl whose status is `completed`
- **THEN** the response is 409 and the status remains `completed`

### Requirement: Crawl failures are reported on the crawl
A crawl whose base URL cannot be fetched SHALL end with status `failed` and an error message saying so. A crawl that stops because of an unexpected internal error SHALL end with status `failed` and an error message, and SHALL NOT affect the service or other crawls. Failures of individual non-base pages SHALL be counted as errors and SHALL NOT fail the crawl.

#### Scenario: Base URL unreachable
- **WHEN** a crawl's base URL fails to fetch
- **THEN** the crawl ends with status `failed` and an error message naming the base URL

#### Scenario: One page fails
- **WHEN** one non-base page of a crawl fails to fetch
- **THEN** the crawl ends with status `completed` and an error count of 1

### Requirement: Health check
The service SHALL answer `GET /health` with status 200 while it is able to accept requests.

#### Scenario: Service is up
- **WHEN** a client requests `GET /health`
- **THEN** the response is 200
