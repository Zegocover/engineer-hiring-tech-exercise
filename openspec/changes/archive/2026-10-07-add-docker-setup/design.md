# Design

## Context

See proposal.md for motivation and specs/containerized-stack/spec.md for behaviour. Paths are relative to `engineer-hiring-tech-exercise/`.

- **The backend** (`python/backend`) is a uv project. Its path dependency `site-crawler = { path = "..", editable = true }` points at the library in `python/`, so the backend can't be built from `python/backend/` alone: the build context must be `python/`.
  - It runs with `uvicorn crawler_api.main:app` and has `GET /health`.
  - Its settings come from `CRAWLER_API_*` variables. `Settings.from_env` rejects an empty string for numeric settings, so unset variables must stay unset rather than be passed as `""`.
  - Its lifespan cancels running crawls on shutdown.
- **The dashboard** (`front-end`) is Next.js 16.4 with `cacheComponents`.
  - The route handlers read `CRAWLER_API_URL` per request (it isn't `NEXT_PUBLIC_`), so one image works with any backend address set at runtime.
  - `public/` is empty and not tracked by git, so it doesn't exist in a fresh checkout. The favicon is `src/app/favicon.ico`.
  - The dashboard's API deliberately has no health route (`/api/health` is a 404 by spec).
- **Next.js standalone output** (`output: "standalone"`) produces `.next/standalone/server.js` with only the traced runtime files. `.next/static` and `public` have to be copied next to it. The server listens on `PORT` and `HOSTNAME`.
- **Tooling:** Docker 28 and Compose v2.39 are installed locally. The engine (Docker Desktop) must be running to build. CI runs on `ubuntu-latest`, which ships Docker and Compose v2.

## Goals / Non-Goals

**Goals:**
- `docker compose up --build` gives a working stack on a machine with only Docker.
- Small, non-root runtime images with health checks and clean shutdown.
- A CI smoke test that proves the whole chain works without internet access: browser-facing API, then dashboard server, then crawler API, then a crawl.

**Non-Goals:**
- Hot-reload development containers, a CLI image, registry publishing, image signing or scanning, and orchestration beyond Compose.
- Changing either app's behaviour.

## Decisions

### 1. Backend image: two stages, uv, non-editable install

```
build context: python/          Dockerfile: python/backend/Dockerfile

stage build  (python:3.13-slim + uv binary copied from ghcr.io/astral-sh/uv:<pinned>)
  /app/pyproject.toml, README.md, src/        <- library
  /app/backend/pyproject.toml, uv.lock, README.md, src/
  RUN cd backend && uv sync --locked --no-dev --no-editable   (with the uv cache mounted)
      -> /app/backend/.venv contains crawler_api AND site_crawler as regular installs

stage runtime  (python:3.13-slim)
  COPY --from=build /app/backend/.venv /app/.venv
  PATH=/app/.venv/bin:$PATH, non-root user "app"
  HEALTHCHECK: python -c urllib.request.urlopen('http://127.0.0.1:8000/health')
  CMD ["uvicorn", "crawler_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- `--no-editable` installs both packages into the virtualenv, so the runtime stage needs no source tree. Only the venv is copied.
- `--locked` uses `python/backend/uv.lock`, so the image gets exactly the versions CI tests. `--no-dev` leaves out pytest, mypy, ruff and respx.
- Both stages use the same base image, so the venv's interpreter path is valid in the runtime stage.
- The exec-form `CMD` makes uvicorn the process that receives SIGTERM, so it runs the lifespan shutdown that cancels crawls.
- `python/.dockerignore` excludes `**/.venv`, `**/__pycache__`, the mypy, pytest and ruff caches, `dist/`, `tests/`, `backend/tests/`, `examples/` and pre-commit config.

Alternatives considered:
- *Build context `python/backend/` with the library vendored or copied in.* That duplicates code, or needs a pre-build copy step.
- *An editable install with sources copied into the runtime stage.* It's larger, and runtime would depend on the source tree's layout.
- *pip with a requirements export.* That loses the guarantee of using the lockfile directly.

### 2. Dashboard image: three stages, standalone output switched on by an environment variable

```
build context: front-end/       Dockerfile: front-end/Dockerfile

stage deps   (node:24-slim)  COPY package.json package-lock.json; RUN npm ci
stage build  FROM deps; COPY . .; ENV NEXT_OUTPUT=standalone NEXT_TELEMETRY_DISABLED=1; RUN npm run build
stage run    (node:24-slim)
  COPY --from=build --chown=node .next/standalone ./
  COPY --from=build --chown=node .next/static ./.next/static
  ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=3000; USER node
  HEALTHCHECK: node -e "fetch('http://127.0.0.1:3000/').then(r=>process.exit(r.ok?0:1),()=>process.exit(1))"
  CMD ["node", "server.js"]
```

`next.config.ts` gains `output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined`. With the variable unset, local `npm run build` and `next start` behave as they do now; `next start` warns when standalone output is on. With it set, only the image build produces standalone output.

- `public/` isn't copied, because it doesn't exist in a clean checkout and copying it would fail the build. If the app ever adds public assets, this is a one-line change.
- The `node` user that comes with the image is the non-root user.
- The health check uses Node's built-in `fetch`, because the slim image has no curl. It requests `/`, a static page, because the dashboard's API exposes no health route.
- `front-end/.dockerignore` excludes `node_modules`, `.next`, `coverage`, `*.tsbuildinfo`, `next-env.d.ts` and `.env*`. This keeps the host's Windows-built `node_modules` and any local env files out of the Linux build.

Alternative: *`next start` with the full `node_modules`.* It's simpler, but the image is several times larger and ships the dev dependencies.

### 3. Compose file at the repo root

```yaml
name: site-crawler
services:
  backend:
    build: { context: ./python, dockerfile: backend/Dockerfile }
    init: true
    ports: ["${BACKEND_PORT:-8000}:8000"]
    environment:            # passed through only when set on the host
      - CRAWLER_API_DEFAULT_MAX_PAGES
      - CRAWLER_API_MAX_PAGES_LIMIT
      - CRAWLER_API_DEFAULT_CONCURRENCY
      - CRAWLER_API_MAX_CONCURRENCY
      - CRAWLER_API_MAX_CONNECTIONS
      - CRAWLER_API_REQUEST_TIMEOUT
      - CRAWLER_API_USER_AGENT
  dashboard:
    build: ./front-end
    init: true
    environment:
      CRAWLER_API_URL: http://backend:8000
    ports: ["${DASHBOARD_PORT:-3000}:3000"]
    depends_on:
      backend: { condition: service_healthy }
```

- The bare `- NAME` form of `environment` passes a variable through only when the host sets it. An unset variable stays unset in the container, which `Settings.from_env` requires.
- `init: true` runs a tiny init process as PID 1, which forwards signals and reaps child processes. Node running as PID 1 doesn't get default signal handling, so without an init process the dashboard could ignore SIGTERM and be killed after 10 seconds.
- Health checks live in the Dockerfiles, so the images are healthy-aware without Compose. Compose's `depends_on: service_healthy` and `up --wait` use them. Short `--start-interval` values keep startup quick.
- The backend port stays published so its `/docs` page can be used for the demo. The dashboard doesn't need it, because it uses the internal network.

### 4. CI smoke test without the internet

A `docker` job runs `docker compose up --build --wait --wait-timeout 180`, then `scripts/docker-smoke.sh`, which uses only curl, bash and python3, all available on the runner and in Git Bash:

1. `GET localhost:3000/api/crawls` returns 200 with `[]`, which proves the browser-facing API reaches the backend through the dashboard.
2. `POST localhost:3000/api/crawls` with `{"url": "http://dashboard:3000/", "max_pages": 5}`: the backend container crawls the dashboard container's own site over the internal network.
3. Poll `/api/crawls/{id}/status` until it's no longer `running`, with a timeout. Expect `completed` and at least 1 page.
4. Check that `docker compose exec backend id -u` and `docker compose exec dashboard id -u` aren't 0.

On failure the job prints `docker compose logs`. It always runs `docker compose down` at the end. Builds use the runner's Docker layer cache; registry caching is left for later.

### 5. Docs

- **Top-level `README.md`:** a short "Run everything with Docker" section covering `docker compose up --build`, the two URLs, the port variables, and how to stop.
- **Backend and dashboard READMEs:** a one-line pointer each.

## Risks / Trade-offs

- [Docker Desktop must be running for local verification; it isn't at the moment] → Implementation starts it before building. Every check also runs in CI on Linux.
- [The pinned uv image tag goes stale] → Pin a specific uv version for reproducibility, and bump it deliberately like any dependency.
- [Next.js standalone tracing misses a file that's needed at runtime] → The CI smoke test exercises the pages and route handlers in the built image. The fix would be `outputFileTracingIncludes`.
- [Crawling the dashboard from the backend in CI looks like crawling an internal address] → That's intended here, to test without the internet. The README already says the API is for trusted use.
- [Two Node images have to be downloaded (`node:24-slim` for deps/build and runtime)] → They're the same tag, so the layer is shared.
- [Line endings: Windows checkouts with `autocrlf` could give shell scripts CRLF endings] → Add `.gitattributes` with `*.sh text eol=lf`. The Dockerfiles contain no shell scripts copied into images.
