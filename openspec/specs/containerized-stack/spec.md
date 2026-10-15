# containerized-stack Specification

## Purpose

Run the crawler API and the crawler dashboard together from container images with one command, so the whole system can be tried or checked without installing Python or Node.

## Requirements

### Requirement: One command starts the whole stack
Running `docker compose up --build` from the repository root SHALL build images for the crawler API and the dashboard and start both. Once started, the dashboard SHALL be usable at `http://localhost:3000` and the crawler API at `http://localhost:8000`, with no other installation or configuration.

#### Scenario: Fresh start
- **WHEN** a user with only Docker installed runs `docker compose up --build` in the repository root
- **THEN** both services become healthy, and `http://localhost:3000` shows the dashboard with an empty crawl list

#### Scenario: Crawl through the containerized stack
- **WHEN** the stack is running and a user starts a crawl from the dashboard
- **THEN** the crawl runs in the crawler API container and its progress and results appear in the dashboard

### Requirement: The dashboard reaches the crawler API inside the stack
The stack SHALL configure the dashboard to call the crawler API at its address on the stack's internal network. The browser SHALL still only talk to the dashboard.

#### Scenario: Dashboard uses the internal address
- **WHEN** the stack is running and the dashboard's API lists crawls
- **THEN** the request reaches the crawler API container through the internal network, and the response is 200

### Requirement: Services report their health
Each service SHALL define a health check: the crawler API through its health endpoint, and the dashboard by serving its home page. The dashboard SHALL NOT be started until the crawler API reports healthy.

#### Scenario: Startup order
- **WHEN** the stack starts
- **THEN** the dashboard container starts only after the crawler API container is healthy, and both report `healthy` once ready

### Requirement: Ports and crawler settings are configurable
The host ports for the dashboard and the crawler API SHALL be configurable through environment variables, defaulting to 3000 and 8000. The crawler API's `CRAWLER_API_*` settings SHALL be passed through from the environment to the crawler API container when set.

#### Scenario: Different dashboard port
- **WHEN** a user runs the stack with `DASHBOARD_PORT=4000`
- **THEN** the dashboard is served at `http://localhost:4000`

#### Scenario: Crawler setting passed through
- **WHEN** a user runs the stack with `CRAWLER_API_DEFAULT_MAX_PAGES=50`
- **THEN** a crawl started without a page budget reports a page budget of 50

### Requirement: Containers run unprivileged with only runtime files
Both images SHALL run their service as a non-root user. They SHALL contain only what is needed at runtime: no development dependencies, test suites, local virtual environments, caches or build tools.

#### Scenario: Non-root
- **WHEN** a user inspects either running container's process user
- **THEN** it isn't root

#### Scenario: No development files
- **WHEN** a user lists the contents of either image
- **THEN** it contains no test directories, no dev-only packages (for example pytest or vitest) and no local `.venv`, `node_modules` cache or `.next/cache` from the build machine

### Requirement: The stack stops cleanly
Stopping the stack with `docker compose down` or Ctrl+C SHALL deliver the stop signal to each service's process. Each service SHALL shut down within Docker's default 10-second grace period without being killed.

#### Scenario: Stop while a crawl runs
- **WHEN** a crawl is running and the user runs `docker compose down`
- **THEN** both containers exit within 10 seconds with exit code 0 (or the code for normal termination by signal), not because they were killed
