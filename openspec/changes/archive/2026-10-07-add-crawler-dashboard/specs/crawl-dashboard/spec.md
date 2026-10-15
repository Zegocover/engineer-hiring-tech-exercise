# Spec Delta

## Purpose

A web dashboard for the crawl API: start crawls, watch them progress, browse the pages and links they find, and cancel them from a browser, without the browser ever talking to the crawl API directly.

## ADDED Requirements

### Requirement: The browser reaches the crawl API only through the dashboard
The dashboard SHALL serve its own same-origin API for every crawl operation it uses, and its server SHALL make the calls to the crawl API. The crawl API's address SHALL be configured on the dashboard's server only and SHALL NOT be sent to the browser. When no address is configured, the dashboard SHALL use `http://localhost:8000`.

#### Scenario: Browser requests stay on the dashboard's origin
- **WHEN** a user starts a crawl and opens it in the dashboard
- **THEN** every request the page makes goes to the dashboard's own `/api/...` paths, none to the crawl API's address

#### Scenario: Configured address is used
- **WHEN** the dashboard's server is configured with a crawl API address of `http://crawler:9000`
- **THEN** the dashboard's API calls the crawl API at `http://crawler:9000`

### Requirement: Only the crawl operations the dashboard needs are exposed
The dashboard's API SHALL expose only these operations: list crawls, start a crawl, read a crawl's details, read its status, read its pages, read its links, and cancel it. It SHALL forward the request's query parameters and body for these operations. Any other path or method under the dashboard's API SHALL return 404 or 405 without contacting the crawl API.

#### Scenario: Unknown path is not forwarded
- **WHEN** a client requests `GET /api/health` or `GET /api/crawls/123/anything` from the dashboard
- **THEN** the response is 404 and no request reaches the crawl API

#### Scenario: Paging parameters are forwarded
- **WHEN** the dashboard's API receives `GET /api/crawls/123/pages?offset=20&limit=10`
- **THEN** it requests the crawl's pages from the crawl API with `offset=20` and `limit=10` and returns that response

### Requirement: Crawl API responses and errors pass through unchanged
For an operation the crawl API answers, the dashboard's API SHALL return the crawl API's status code and JSON body unchanged, including error responses (for example 404 for an unknown crawl, 409 for cancelling a finished crawl, 422 for an invalid request).

#### Scenario: Validation error passed through
- **WHEN** the crawl API rejects a start request with 422 and a list of validation errors
- **THEN** the dashboard's API responds 422 with the same body

#### Scenario: Not found passed through
- **WHEN** the crawl API responds 404 for an unknown crawl
- **THEN** the dashboard's API responds 404 with the same body

### Requirement: An unreachable crawl API is reported clearly
When the crawl API cannot be reached or does not respond within the dashboard's timeout, the dashboard's API SHALL respond 502 with a `detail` saying the crawl API is unreachable. The dashboard's pages SHALL show that message instead of failing silently or showing a blank page, and SHALL recover without a page reload once the crawl API is reachable again.

#### Scenario: Backend down
- **WHEN** the crawl API is not running and a user opens the dashboard
- **THEN** the dashboard's API responds 502 and the page shows that the crawl API is unreachable

#### Scenario: Backend comes back
- **WHEN** the crawl API becomes reachable again while the dashboard is open
- **THEN** the crawl list loads on its next refresh without the user reloading the page

### Requirement: Users can start a crawl
The dashboard SHALL provide a form with a required URL and optional page budget, depth, concurrency and robots.txt setting, which defaults to respecting robots.txt. Submitting it SHALL start a crawl and open that crawl's view. The submit button SHALL be disabled while the request is in flight.

#### Scenario: Start and open the crawl
- **WHEN** a user enters `https://example.com/` and submits the form
- **THEN** a crawl is started with that URL and the dashboard shows the new crawl's view

#### Scenario: Optional limits left empty
- **WHEN** a user submits the form with only a URL
- **THEN** the start request contains only `url` and `respect_robots`, so the crawl API applies its own defaults

### Requirement: Rejected crawl requests show why
When starting a crawl is rejected, the form SHALL show each error message from the response, next to the field it names when it names one, and otherwise at the top of the form. The form SHALL keep the values the user entered.

#### Scenario: Field error shown next to the field
- **WHEN** the crawl API rejects a start request with an error located at `max_depth`
- **THEN** that error's message appears next to the depth field and the entered values remain

#### Scenario: General error shown on the form
- **WHEN** the crawl API rejects a start request with an error not tied to a field (for example an `ftp://` URL)
- **THEN** that error's message appears at the top of the form

### Requirement: Users can see all crawls
The dashboard SHALL list every crawl, newest first. Each entry SHALL show its URL, status, pages reported and error count, and link to its view. While any listed crawl is running, the list SHALL refresh periodically. When none is running, it SHALL stop refreshing on a timer. An empty list SHALL say that no crawls have been started.

#### Scenario: Crawls listed with status
- **WHEN** two crawls exist, one completed and one running
- **THEN** both are listed with the newer first, each showing its URL, status, pages and errors

#### Scenario: List refreshes while a crawl runs
- **WHEN** a listed crawl is running and reports more pages
- **THEN** the list shows the new page count without a manual reload

### Requirement: Users can follow a crawl as it runs
A crawl's view SHALL show its URL, status, start and finish times, statistics (pages, fetched, errors, skipped by robots.txt), effective limits and error message, if any. While the crawl is running, the view SHALL poll its status about once a second and update. Once the status is no longer `running`, it SHALL stop polling.

#### Scenario: Live progress
- **WHEN** a user views a running crawl whose page count increases
- **THEN** the displayed page count increases without a manual reload

#### Scenario: Polling stops when finished
- **WHEN** the viewed crawl's status changes to `completed`
- **THEN** the view shows `completed` and the finish time, and makes no further status requests

#### Scenario: Failed crawl shows its error
- **WHEN** the viewed crawl has status `failed` with an error message
- **THEN** the view shows the status and the error message

#### Scenario: Unknown crawl
- **WHEN** a user opens the view for a crawl id the crawl API doesn't know
- **THEN** the dashboard shows that the crawl was not found, with a link back to the list

### Requirement: Users can browse a crawl's pages and links
A crawl's view SHALL have a pages tab and a links tab. The pages tab SHALL list the reported pages in order with each page's links. The links tab SHALL list the distinct links found. Both SHALL be paged, showing the total and the current range, with controls for the next and previous page that are disabled at either end. While the crawl is running, the shown page of results SHALL refresh as new results arrive.

#### Scenario: Next page of pages
- **WHEN** a crawl has 120 pages, the page size is 50, and the user moves to the next page in the pages tab
- **THEN** pages 51 to 100 are shown with the total of 120, and both previous and next are enabled

#### Scenario: Links tab
- **WHEN** a user opens the links tab of a crawl that found 3 distinct links
- **THEN** the 3 links are shown with a total of 3, and the next and previous controls are disabled

### Requirement: Users can cancel a running crawl
A running crawl's view SHALL offer a cancel action. Using it SHALL cancel the crawl and show its `cancelled` status, with the pages already found still browsable. A crawl that isn't running SHALL NOT offer the action. If the crawl finishes before the cancel request arrives, the view SHALL show the crawl's actual final status instead of an error page.

#### Scenario: Cancel a running crawl
- **WHEN** a user cancels a running crawl
- **THEN** the view shows `cancelled`, polling stops, and the pages tab still lists the pages found

#### Scenario: Cancel loses the race
- **WHEN** the crawl completes just before the user's cancel request reaches it and the crawl API responds 409
- **THEN** the view shows the crawl as `completed`

#### Scenario: No cancel for finished crawls
- **WHEN** a user views a completed crawl
- **THEN** no cancel action is offered
