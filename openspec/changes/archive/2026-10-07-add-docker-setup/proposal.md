# Proposal

## Why

Running the demo today means installing both Python with uv and Node, then starting two processes in two terminals with the right settings. A reviewer who just wants to see the crawler working has to follow two READMEs. Container images and a Compose file reduce that to `docker compose up`. They also give the backend and dashboard a reproducible runtime that can be checked in CI from a clean machine.

## What Changes

- **Backend image.** Add `python/backend/Dockerfile`, built from the `python/` folder, because the backend installs the `site-crawler` library from its parent directory. Add `python/.dockerignore` to keep virtualenvs, caches and build output out of the build.
- **Dashboard image.** Add `front-end/Dockerfile` and `front-end/.dockerignore`, using Next.js standalone output. Standalone output is only switched on for image builds, so local `npm run dev`, `npm run build` and `next start` behave exactly as now.
- **Both images:**
  - contain only what the app needs to run (no dev dependencies, tests or caches);
  - run as a non-root user;
  - define a health check.
- **One-command stack.** Add `compose.yaml` at the repo root (`engineer-hiring-tech-exercise/`). `docker compose up --build` builds both images and starts:
  - the backend on port 8000;
  - the dashboard on port 3000, wired to the backend over Compose's internal network via `CRAWLER_API_URL=http://backend:8000`.

  The dashboard starts once the backend is healthy. Host ports and the backend's `CRAWLER_API_*` settings can be overridden through environment variables.
- **CI.** Add a `docker` job that builds both images, starts the stack and waits for it to be healthy. It then runs a crawl end to end through the dashboard's API: the backend crawls the dashboard's own site over the internal network, so the smoke test doesn't depend on the internet. Nothing is pushed to a registry.
- **Docs.** Add a "Run everything with Docker" section to the top-level README and pointers from the backend and dashboard READMEs.
- **Out of scope:** a development mode with hot reload inside containers, a container image for the `crawl` CLI, publishing images, and production hardening beyond non-root, health checks and small images.

## Capabilities

### New Capabilities

- `containerized-stack`: running the crawler API and the dashboard together from container images with one command, including how they're wired together, how they report health, what can be configured, and how they stop.

### Modified Capabilities

None.

- `crawl-api` and `crawl-dashboard` behave the same inside containers. The dashboard already reads `CRAWLER_API_URL` at request time, and the backend already reads `CRAWLER_API_*` settings.
- The only app-level edit is opting the dashboard's build into standalone output through an environment variable, which changes no specified behaviour.

## Impact

- **New files:**
  - `python/backend/Dockerfile` and `python/.dockerignore`;
  - `front-end/Dockerfile` and `front-end/.dockerignore`;
  - `compose.yaml` at the repo root;
  - `scripts/docker-smoke.sh`, the CI smoke test, which can also be run locally;
  - `.gitattributes`, which keeps shell scripts on LF line endings.
- **Changed:**
  - `front-end/next.config.ts` (standalone output when building the image);
  - `.github/workflows/ci.yml` (a new `docker` job);
  - `README.md`, `python/backend/README.md` and `front-end/README.md` (docs).
- **Developers:** Docker with Compose v2 is needed only for this path; the existing uv and npm workflows are unchanged. Docker Desktop must be running to build locally.
- **CI time:** one more job, which builds two images. Layer caching keeps rebuilds fast.
