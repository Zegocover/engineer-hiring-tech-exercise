# crawler-extension-api Specification

## Purpose

Let consumers of the crawler package replace how pages are fetched, how links are extracted and where results are written, while the package keeps ownership of crawl correctness (scope, de-duplication, normalisation, termination).

## Requirements

### Requirement: Consumers can supply a custom fetcher
The package SHALL let a consumer provide their own component that, given a URL, returns the requested URL, final URL, status, content type and body, or signals a fetch failure. The crawl SHALL use it for every request in place of the default.

#### Scenario: Custom fetcher serves a fake site
- **WHEN** a consumer supplies a fetcher that returns canned pages from memory
- **THEN** the crawl reports those pages and makes no network requests

#### Scenario: Custom fetcher signals failure
- **WHEN** the consumer's fetcher signals a fetch failure for one URL
- **THEN** that URL is recorded as an error and the crawl continues

### Requirement: Consumers can supply a custom parser
The package SHALL let a consumer provide their own component that, given a fetched page, returns the raw link strings found in it. The package SHALL resolve, normalise, filter and de-duplicate those strings itself, so a consumer parser cannot make the crawl leave its host or fetch a URL twice.

#### Scenario: Parser returns relative and off-host links
- **WHEN** a custom parser returns `next`, `/next`, `https://other.org/` and `next#top` for a page at `https://example.com/dir/`
- **THEN** the crawl reports normalised links and fetches `https://example.com/dir/next` and `https://example.com/next` once each, and does not fetch `https://other.org/`

### Requirement: Consumers can supply a custom writer
The package SHALL let a consumer provide their own component that receives each page result (page URL and its normalised links). Results SHALL be delivered one at a time, never concurrently, and the writer SHALL be given a chance to flush or close when the crawl ends.

#### Scenario: Collecting writer
- **WHEN** a consumer supplies a writer that appends results to a list
- **THEN** after the crawl the list contains one entry per reported page, and the writer's close step has run exactly once

### Requirement: Custom components need no package inheritance
A consumer component SHALL be accepted when it provides the required operations, without having to subclass or register with any package type.

#### Scenario: Plain class as writer
- **WHEN** a consumer passes an instance of a plain class that only defines the required write and close operations
- **THEN** the crawl runs using it

### Requirement: Defaults are used when nothing is supplied
The package SHALL provide a default fetcher (HTTP), parser (HTML `<a href>`) and writer (standard output). A crawl created without custom components SHALL use them.

#### Scenario: Programmatic crawl with defaults
- **WHEN** a consumer creates a crawl with only a base URL and configuration
- **THEN** it crawls over HTTP, parses HTML anchors and writes to standard output

### Requirement: Programmatic crawl returns a summary
Running a crawl programmatically SHALL return a summary with at least the number of pages reported, URLs fetched and errors.

#### Scenario: Summary after crawl
- **WHEN** a crawl of a fake three-page site with one failing page finishes
- **THEN** the returned summary reports 2 pages and 1 error

### Requirement: Unexpected component errors stop the crawl
If a consumer component raises an error other than the documented fetch-failure signal, the crawl SHALL stop and propagate that error to the caller after closing the writer, rather than silently continuing.

#### Scenario: Parser bug
- **WHEN** a custom parser raises an unexpected exception
- **THEN** the crawl stops, the writer is closed, and the exception reaches the caller
