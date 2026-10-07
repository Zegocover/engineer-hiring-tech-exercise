# Spec Delta

## MODIFIED Requirements

### Requirement: Users can start a crawl
The dashboard SHALL provide a form with a required URL and these optional settings:
- page budget, depth, concurrency and per-host concurrency;
- a robots.txt setting, which defaults to respecting robots.txt;
- an "also follow hosts" field taking host patterns, one per line or separated by commas.

Submitting the form SHALL start a crawl and open that crawl's view. The submit button SHALL be disabled while the request is in flight.

#### Scenario: Start and open the crawl
- **WHEN** a user enters `https://example.com/` and submits the form
- **THEN** a crawl is started with that URL and the dashboard shows the new crawl's view

#### Scenario: Optional limits left empty
- **WHEN** a user submits the form with only a URL
- **THEN** the start request contains only `url` and `respect_robots`, so the crawl API applies its own defaults

#### Scenario: Also follow hosts
- **WHEN** a user enters `*.example.com` and `docs.partner.io` (on separate lines, or separated by a comma) in the "also follow hosts" field and submits
- **THEN** the start request contains `allowed_hosts` `["*.example.com", "docs.partner.io"]`, with blank entries and surrounding spaces removed

### Requirement: Users can follow a crawl as it runs
A crawl's view SHALL show:
- its URL, status, and start and finish times;
- statistics: pages, fetched, errors, and skipped by robots.txt;
- effective limits, including the allowed host patterns (or that only the base host is followed) and the per-host concurrency limit;
- its error message, if any.

While the crawl is running, the view SHALL poll its status about once a second and update. Once the status is no longer `running`, it SHALL stop polling.

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

#### Scenario: Allowed hosts shown
- **WHEN** a user views a crawl started with allowed hosts `*.example.com` and `docs.partner.io`
- **THEN** the limits show both patterns, and a crawl started without any shows that only the base host is followed
