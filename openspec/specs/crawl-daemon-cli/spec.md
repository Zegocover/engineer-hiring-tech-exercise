# crawl-daemon-cli Specification

## Purpose

Gives command-line users one command, `crawld`, to run the crawl daemon and to submit, follow, inspect and cancel its crawl jobs from a shell or a script.

## Requirements

### Requirement: The daemon can run in the foreground
`crawld serve` SHALL run the daemon in the current process until it is stopped. It SHALL accept options for the port, data directory, database URL, maximum number of parallel jobs and log level, and SHALL write its logs to standard error.

#### Scenario: Serve in the foreground
- **WHEN** a user runs `crawld serve --port 8765`
- **THEN** the daemon accepts jobs on port 8765 until the user presses Ctrl+C, after which it stops cleanly and the command exits with status 0

### Requirement: The daemon can be started in the background
`crawld start` SHALL launch the daemon as a background process detached from the terminal. It takes the same options as `serve`, and its logs go to a file in the data directory. It SHALL return only once the daemon is accepting jobs, or once startup has failed.

#### Scenario: Start in the background
- **WHEN** a user runs `crawld start`
- **THEN** the command exits with status 0 and prints the daemon's port and process id, `crawld ping` succeeds, and closing the terminal does not stop the daemon

#### Scenario: Already running
- **WHEN** a daemon is running and a user runs `crawld start` with the same data directory
- **THEN** the command prints that the daemon is already running and exits with status 0, without starting a second daemon

#### Scenario: Startup fails
- **WHEN** a user runs `crawld start` with a port that is already in use
- **THEN** the command exits with a non-zero status and prints the daemon's startup error

### Requirement: The daemon can be stopped and checked
`crawld stop` SHALL ask the running daemon to stop and SHALL wait until it has exited. `crawld ping` SHALL report whether a daemon is running, with its port, process id, and numbers of running and queued jobs.

#### Scenario: Stop a running daemon
- **WHEN** a daemon is running and a user runs `crawld stop`
- **THEN** the command exits with status 0 once the daemon process has exited

#### Scenario: Ping with no daemon
- **WHEN** no daemon is running and a user runs `crawld ping`
- **THEN** the command prints that the daemon is not running and exits with the "daemon not running" status

### Requirement: Users can submit jobs from the command line
`crawld submit URL` SHALL submit a job and print its identifier. It SHALL accept the same crawl options as the `crawl` command where the daemon supports them: `--max-pages`, `--max-depth`, `-c/--concurrency`, `--per-host-concurrency`, `--allow-host` (repeatable) and `--no-robots`.

#### Scenario: Submit and get an identifier
- **WHEN** a user runs `crawld submit https://example.com/ --max-pages 50`
- **THEN** the command prints the new job's identifier and exits with status 0 without waiting for the crawl

#### Scenario: Rejected submission
- **WHEN** a user runs `crawld submit ftp://example.com/`
- **THEN** the command prints the daemon's description of the problem to standard error and exits with the usage-error status

### Requirement: Users can wait for a job to finish
`crawld submit --wait`, and `crawld wait ID`, SHALL show the job's progress on standard error until it finishes, then print its final status. They SHALL exit with status 0 if the job completed and with the job-failed status if it failed or was cancelled. Interrupting the wait SHALL NOT cancel the job.

#### Scenario: Wait for a successful job
- **WHEN** a user runs `crawld submit https://example.com/ --wait` and the crawl completes
- **THEN** the command prints the job's final statistics and exits with status 0

#### Scenario: Interrupting the wait
- **WHEN** a user presses Ctrl+C while `crawld wait ID` is waiting on a running job
- **THEN** the command exits, and the job keeps running

### Requirement: Users can inspect jobs from the command line
`crawld list` (optionally `--status S`) SHALL print jobs, newest first. `crawld status ID` SHALL print a job's details. `crawld pages ID` and `crawld links ID` SHALL print a job's pages and distinct links, with `--offset` and `--limit` options, or all of them with `--all`.

#### Scenario: Print pages like the crawl command
- **WHEN** a user runs `crawld pages ID --all` for a completed job
- **THEN** each page is printed in the same text layout as the `crawl` command's default output, in the order the crawl reported them

#### Scenario: Unknown job
- **WHEN** a user runs `crawld status` with an identifier the daemon has never issued
- **THEN** the command prints that the job was not found to standard error and exits with the not-found status

### Requirement: Users can cancel jobs from the command line
`crawld cancel ID` SHALL cancel a queued or running job and print its final status. Cancelling a finished job SHALL print why it could not be cancelled and exit with the conflict status.

#### Scenario: Cancel a running job
- **WHEN** a user runs `crawld cancel ID` for a running job
- **THEN** the command prints that the job is `cancelled` and exits with status 0

### Requirement: Output is available as JSON
Every job command (`submit`, `wait`, `list`, `status`, `pages`, `links`, `cancel`) and `ping` SHALL accept `--json`. With it, the command SHALL print exactly one JSON document to standard output, holding the daemon's answer, or, for `pages --all` and `links --all`, one JSON object per line.

#### Scenario: Status as JSON
- **WHEN** a user runs `crawld status ID --json`
- **THEN** standard output is a single JSON object containing the job's `id`, `status`, `limits` and `stats`

### Requirement: Exit codes distinguish failure causes
The command SHALL exit with 0 on success, 1 if a waited-on job failed or was cancelled, 2 on a usage error or rejected request, 3 if no daemon is running, 4 for an unknown job, 5 for a conflict, and 130 when interrupted. Error messages SHALL go to standard error.

#### Scenario: No daemon running
- **WHEN** no daemon is running and a user runs `crawld list`
- **THEN** the command prints that the daemon is not running, suggests `crawld start`, and exits with status 3

### Requirement: The command finds the daemon through its data directory
Client commands SHALL locate the daemon, and get its token, from the state file in the data directory. The data directory SHALL default to a per-user location and SHALL be overridable with `--data-dir` or the `CRAWLD_DATA_DIR` environment variable.

#### Scenario: Custom data directory
- **WHEN** a daemon was started with `--data-dir ./d` and a user runs `crawld list --data-dir ./d`
- **THEN** the command talks to that daemon
