# Spec Delta

## Purpose

Lets a local user run site crawls in the background: a long-running process accepts crawl jobs, queues them, runs a bounded number at a time, and reports their progress and results until the user asks for them.

## ADDED Requirements

### Requirement: The daemon accepts connections only from the local machine
The daemon SHALL listen for client connections only on the loopback interface, on a configurable port. While it is accepting jobs, it SHALL keep a state file in its data directory that records its port, its process id and an access token.

#### Scenario: Listening on loopback
- **WHEN** the daemon is started with port 8765
- **THEN** it accepts connections at `127.0.0.1:8765`, and the state file in its data directory names port 8765, the daemon's process id and a token

#### Scenario: Port already in use
- **WHEN** the daemon is started on a port that another process is already listening on
- **THEN** it exits with an error naming the port and does not write a state file

### Requirement: Requests must carry the daemon's token
The daemon SHALL reject any request that lacks the token from its current state file, or carries a different one, with an `unauthorized` error, and SHALL NOT act on that request. A new token SHALL be generated each time the daemon starts.

#### Scenario: Missing token
- **WHEN** a client sends a request to submit a job without a token
- **THEN** the daemon answers with an `unauthorized` error and no job is created

#### Scenario: Token from a previous run
- **WHEN** a client sends a request with the token written by an earlier run of the daemon
- **THEN** the daemon answers with an `unauthorized` error

### Requirement: Only one daemon runs per data directory
The daemon SHALL refuse to start if another daemon using the same data directory is running and answering requests. It SHALL replace a state file left by a daemon that is no longer running.

#### Scenario: Second daemon refused
- **WHEN** a daemon is running and a second daemon is started with the same data directory
- **THEN** the second one exits with an error saying a daemon is already running, and the first keeps running

#### Scenario: Stale state file
- **WHEN** the state file names a daemon process that has exited, and a daemon is started
- **THEN** the daemon starts and writes a new state file

### Requirement: Clients can submit a crawl job
The daemon SHALL accept a job that crawls a base URL with optional limits: page budget, depth, concurrency, per-host concurrency, robots.txt handling and additional allowed host patterns. It SHALL answer immediately with the new job's unique identifier and status, without waiting for the crawl to run.

#### Scenario: Submit a job
- **WHEN** a client submits a job for `https://example.com/` while no other job is running
- **THEN** the daemon answers at once with a new job identifier, and the job's status becomes `running`

#### Scenario: Submit with allowed hosts
- **WHEN** a client submits a job for `https://example.com/` with allowed hosts `["*.example.com"]` and per-host concurrency 2
- **THEN** the job follows links into subdomains of `example.com` with at most 2 requests to any one host at a time

### Requirement: Invalid jobs are rejected
The daemon SHALL reject a submission whose URL is not an absolute `http` or `https` URL, whose limits are out of range, or whose allowed host patterns are invalid, with an `invalid_request` error that describes the problem. No job SHALL be created for a rejected submission.

#### Scenario: Non-HTTP URL
- **WHEN** a client submits a job for `ftp://example.com/`
- **THEN** the daemon answers with an `invalid_request` error, and listing jobs shows no new job

#### Scenario: Negative depth
- **WHEN** a client submits a job with a depth limit of `-1`
- **THEN** the daemon answers with an `invalid_request` error

### Requirement: Daemon limits bound every job
The daemon SHALL apply a default page budget and a default concurrency when a submission does not set them. It SHALL reject a submission whose page budget, concurrency or per-host concurrency is above the daemon's configured maximum, with an `invalid_request` error.

#### Scenario: Default page budget applied
- **WHEN** a client submits a job without a page budget
- **THEN** the job's reported limits show the daemon's default page budget, and it reports no more pages than that budget

#### Scenario: Page budget above the maximum
- **WHEN** a client submits a job whose page budget is above the daemon's maximum
- **THEN** the daemon answers with an `invalid_request` error and no job is created

### Requirement: Jobs are queued and run with bounded parallelism
The daemon SHALL run at most a configured number of jobs at once (2 by default). Any further jobs SHALL wait with status `queued` and start in the order they were submitted as running jobs finish.

#### Scenario: Job waits for a free slot
- **WHEN** the daemon allows 1 job at a time, and a client submits job A and then job B
- **THEN** B's status is `queued` while A is `running`, and B becomes `running` once A finishes

#### Scenario: First in, first out
- **WHEN** the daemon allows 1 job at a time, and jobs B and C are queued in that order behind a running job
- **THEN** B starts before C

### Requirement: Jobs run independently
A job's results, statistics, failure or cancellation SHALL NOT affect any other job.

#### Scenario: Cancelling one job leaves another running
- **WHEN** two jobs are running and a client cancels the first
- **THEN** the second keeps running and later reaches `completed` with its own results

### Requirement: Jobs follow the site-crawl rules
Each job SHALL follow the same crawl rules as the command-line crawl. It SHALL stay within its crawl scope, fetch each normalised URL at most once, report normalised links, and respect each host's robots.txt unless the submission disables that.

#### Scenario: Off-host link reported but not fetched
- **WHEN** a crawled page links to `https://other.org/` and `other.org` is not allowed
- **THEN** that link appears in the page's links, and no page for `https://other.org/` appears in the job's results

### Requirement: Clients can read a job's details
For a known job, the daemon SHALL return its identifier, base URL, effective limits, status (`queued`, `running`, `completed`, `failed` or `cancelled`), submission, start and finish times, statistics (including parse-cache hits), and error message if any. An unknown identifier SHALL produce a `not_found` error.

#### Scenario: Details of a queued job
- **WHEN** a client asks for the details of a job that has not started yet
- **THEN** the answer has status `queued`, a submission time, no start or finish time, and zero pages

#### Scenario: Unknown job
- **WHEN** a client asks for a job identifier the daemon has never issued
- **THEN** the daemon answers with a `not_found` error

### Requirement: Clients can list jobs
The daemon SHALL list every job it holds, most recently submitted first, giving each job's identifier, base URL, status and statistics. The listing SHALL be filterable by status.

#### Scenario: Two jobs listed
- **WHEN** a client submits a job for `https://a.example/` and then one for `https://b.example/`, then lists jobs
- **THEN** both are listed, with the `https://b.example/` job first

#### Scenario: Filter by status
- **WHEN** one job is `completed` and another is `running`, and a client lists jobs with status `running`
- **THEN** only the running job is listed

### Requirement: Clients can page through a job's pages and links
The daemon SHALL return a job's pages in the order the crawl reported them, each with its URL and links. It SHALL also return the job's distinct links in the order each was first found. Both SHALL use an offset and a limit, include the total so far, and be readable while the job runs.

#### Scenario: Read pages in slices
- **WHEN** a job has reported 5 pages and a client asks for its pages with offset 2 and limit 2
- **THEN** the answer contains the third and fourth reported pages and a total of 5

#### Scenario: Links are de-duplicated across pages
- **WHEN** the home page links to `/a` and `/b`, and `/a` links to `/b` and `/c`
- **THEN** the job's links are `/a`, `/b` and `/c` (as absolute URLs), once each, in that order, with a total of 3

#### Scenario: Results of an unknown job
- **WHEN** a client asks for the pages of a job identifier the daemon has never issued
- **THEN** the daemon answers with a `not_found` error

### Requirement: Clients can cancel a queued or running job
The daemon SHALL cancel a queued job without starting it. A running job SHALL stop fetching and keep the pages it has already reported. Either way, the job SHALL end as `cancelled`. Cancelling a finished job SHALL produce a `conflict` error and leave its status unchanged.

#### Scenario: Cancel a running job
- **WHEN** a client cancels a running job that has reported 3 pages
- **THEN** the job's status becomes `cancelled`, it fetches no further URLs, and its results still contain the 3 pages

#### Scenario: Cancel a queued job
- **WHEN** a client cancels a job whose status is `queued`
- **THEN** its status becomes `cancelled` and it never starts

#### Scenario: Cancel a finished job
- **WHEN** a client cancels a job whose status is `completed`
- **THEN** the daemon answers with a `conflict` error and the status remains `completed`

### Requirement: Job failures are reported on the job
A job whose base URL cannot be fetched, or that stops on an unexpected internal error, SHALL end as `failed` with an error message, and SHALL NOT affect the daemon or other jobs. Failures of individual non-base pages SHALL be counted as errors and SHALL NOT fail the job.

#### Scenario: Base URL unreachable
- **WHEN** a job's base URL fails to fetch
- **THEN** the job ends with status `failed` and an error message naming the base URL

#### Scenario: One page fails
- **WHEN** one non-base page of a job fails to fetch
- **THEN** the job ends with status `completed` and an error count of 1

### Requirement: Clients can stop the daemon
When asked to stop, the daemon SHALL accept no new requests, cancel its running jobs (they end as `cancelled`), leave queued jobs queued, remove its state file and exit. It SHALL do the same when it receives an interrupt or termination signal.

#### Scenario: Stop with work outstanding
- **WHEN** the daemon is asked to stop while job A is running and job B is queued
- **THEN** A ends as `cancelled` with the pages it had reported, B is still `queued`, the state file is removed, and the process exits

### Requirement: Jobs survive a daemon restart
When it starts, the daemon SHALL load the jobs it holds. Queued jobs SHALL run in their original order. Jobs left `running` by a daemon that exited without stopping cleanly SHALL be marked `failed`, with an error saying the daemon stopped before the crawl finished, and SHALL keep the pages they had reported.

#### Scenario: Queued job resumes
- **WHEN** the daemon is stopped while a job is queued, and is then started again
- **THEN** that job runs and reaches a final status

#### Scenario: Interrupted job after a crash
- **WHEN** the daemon process is killed while a job that has reported 4 pages is running, and the daemon is then started again
- **THEN** that job has status `failed`, an error saying the daemon stopped before the crawl finished, and its 4 pages

### Requirement: Malformed requests are rejected without disconnecting the daemon
The daemon SHALL answer a request it cannot parse, or one that names an unknown operation, with an `invalid_request` error, and SHALL keep serving other clients. A request larger than the daemon's size limit SHALL be rejected and that connection closed.

#### Scenario: Unknown operation
- **WHEN** a client with a valid token sends a request for operation `explode`
- **THEN** the daemon answers with an `invalid_request` error and still answers requests from other clients
