# Spec Delta

## Purpose

Keeps crawl jobs and the pages and links they find in a database, either a local SQLite file or a PostgreSQL server. Results are saved while each crawl runs, and they can be read during the crawl, after it ends, and after a restart. The same database also holds a cache of parsed links, so a page that has not changed is not parsed again.

## ADDED Requirements

### Requirement: Storage is selected by a database URL
Storage SHALL be chosen by a database URL. A `sqlite:///PATH` URL, and the default when none is given, SHALL use a SQLite file (by default `crawld.db` in the data directory). A `postgresql://` URL SHALL use that PostgreSQL database. Any other scheme SHALL be rejected at startup.

#### Scenario: Default storage
- **WHEN** the daemon starts without a database URL
- **THEN** it stores jobs in `crawld.db` in its data directory, creating the file if needed

#### Scenario: PostgreSQL storage
- **WHEN** the daemon starts with `postgresql://user@localhost/crawls`
- **THEN** it stores jobs in that database

#### Scenario: Unsupported scheme
- **WHEN** the daemon starts with `mysql://localhost/crawls`
- **THEN** it exits with an error naming the supported schemes

### Requirement: PostgreSQL support is optional
The PostgreSQL driver SHALL be installed only with the `postgres` extra. Choosing a `postgresql://` URL without it SHALL fail at startup with a message saying how to install the extra. SQLite SHALL need no extra dependency.

#### Scenario: Driver not installed
- **WHEN** the `postgres` extra is not installed and the daemon starts with a `postgresql://` URL
- **THEN** it exits with an error telling the user to install `crawl-daemon[postgres]`

### Requirement: The schema is created automatically
On startup, storage SHALL create any tables it needs that do not exist yet. It SHALL leave existing data unchanged, and SHALL refuse to use a database whose schema version is newer than it understands.

#### Scenario: Empty database
- **WHEN** the daemon starts against an empty PostgreSQL database
- **THEN** it creates its tables and accepts jobs

#### Scenario: Existing data kept
- **WHEN** the daemon starts against a database that already holds jobs
- **THEN** those jobs and their results are still listed

#### Scenario: Newer schema
- **WHEN** the daemon starts against a database whose recorded schema version is higher than the one it supports
- **THEN** it exits with an error and does not modify the database

### Requirement: Pages are stored as the crawl reports them
Each page a crawl reports SHALL be stored with its URL, its links in document order, and its position in the job's report order. Pages SHALL be readable while the crawl runs, at most a short, bounded delay after being reported, and SHALL all be stored by the time the job's final status is recorded.

#### Scenario: Pages visible during a crawl
- **WHEN** a running job has reported 20 pages and a client reads its pages after the flush interval has passed
- **THEN** all 20 pages are returned, in report order

#### Scenario: All pages stored at completion
- **WHEN** a job finishes as `completed` after reporting 37 pages
- **THEN** reading its pages returns exactly 37 pages, each with its links in document order

### Requirement: Distinct links are stored once per job
Storage SHALL record each distinct link found on a job's pages once per job, in first-found order, including links that were not followed. The same link found by two different jobs SHALL be recorded for each.

#### Scenario: Repeated link stored once
- **WHEN** three pages of one job all link to `https://example.com/about`
- **THEN** that job's links contain `https://example.com/about` exactly once

#### Scenario: Same link in two jobs
- **WHEN** two jobs both find `https://example.com/about`
- **THEN** it appears in the links of each job

### Requirement: Job state and statistics are stored
Storage SHALL record each job's base URL, effective limits, status, submission, start and finish times, error message, and statistics. Statistics SHALL be updated while the job runs, and SHALL be final once the job's final status is recorded.

#### Scenario: Final statistics stored
- **WHEN** a job finishes with 10 pages, 11 fetched URLs and 1 error, and the daemon is restarted
- **THEN** the job's details show 10 pages, 11 fetched URLs and 1 error

### Requirement: Both databases behave the same
SQLite and PostgreSQL storage SHALL give the same results for the same sequence of operations: the same orderings, totals, slices, filters and stored values.

#### Scenario: Same pages from either database
- **WHEN** the same crawl of a fixed test site is run once with SQLite storage and once with PostgreSQL storage
- **THEN** reading the job's pages and links returns identical results from both

### Requirement: Parsed links are cached by page content
When the parse cache is enabled, the links parsed from an HTML page SHALL be stored keyed by the page's content and final URL. A later fetch of identical content at the same final URL, in any job and after a restart, SHALL reuse them, give the same links as parsing would, and count a parse-cache hit in the job's statistics.

#### Scenario: Unchanged site crawled twice
- **WHEN** a job crawls a fixed 5-page site, and a second job then crawls the same unchanged site
- **THEN** both jobs report identical pages and links, and the second job's statistics show 5 parse-cache hits

#### Scenario: Cache survives a restart
- **WHEN** a job crawls a fixed site, the daemon is restarted, and a new job crawls the same unchanged site
- **THEN** the new job's statistics show a parse-cache hit for every page

### Requirement: Changed pages are parsed again
A page whose content or final URL differs from every cached entry SHALL be parsed, and its new links SHALL be reported and cached.

#### Scenario: Page content changed
- **WHEN** a page was cached with a link to `/old`, and its content changes to link to `/new` before a second job crawls it
- **THEN** the second job reports a link to `/new` and not `/old` for that page, and counts no parse-cache hit for it

### Requirement: Parse-cache failures never fail a crawl
If reading from or writing to the parse cache fails, the page SHALL be parsed normally, and the crawl SHALL carry on and report the same links as it would without a cache.

#### Scenario: Cache read fails
- **WHEN** looking up the parse cache fails for every page of a job
- **THEN** the job completes with the same pages and links as an uncached crawl, and 0 parse-cache hits

### Requirement: The parse cache can be disabled
The daemon SHALL use the parse cache by default and SHALL provide a setting that turns it off. With it off, no parse-cache entries SHALL be read or written.

#### Scenario: Cache disabled
- **WHEN** the daemon runs with the parse cache turned off, and the same unchanged site is crawled twice
- **THEN** both jobs show 0 parse-cache hits and no parse-cache entries are stored

### Requirement: A storage failure fails only the affected job
If storage fails while a crawl is writing results, that job SHALL end as `failed` with an error message describing the storage failure, if that can still be recorded. The daemon and other jobs SHALL keep running.

#### Scenario: Write fails mid-crawl
- **WHEN** writing a page for one running job fails, while another job is also running
- **THEN** the first job ends as `failed` with a storage error message, and the second job continues
