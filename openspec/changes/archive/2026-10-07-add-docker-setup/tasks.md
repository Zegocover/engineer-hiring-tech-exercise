# Tasks

Paths are relative to `engineer-hiring-tech-exercise/`. Docker Desktop must be running for every `docker` command.

## 1. Backend image

- [x] 1.1 Add `python/.dockerignore` and `python/backend/Dockerfile` (two stages: python:3.13-slim with a pinned uv runs `uv sync --locked --no-dev --no-editable` in `backend/`, then the runtime stage copies only the venv, runs as a non-root `app` user, has a `/health` HEALTHCHECK and an exec-form uvicorn CMD on 0.0.0.0:8000); verify `docker build -f python/backend/Dockerfile python` succeeds, and that a container from it answers `GET /health` with 200, runs as a non-zero uid, and has no `pytest`, `tests/` or `.venv` from the host (`docker run --rm --entrypoint sh <image> -c 'id -u; pip list 2>/dev/null | grep -ci pytest; ls /app'`)

## 2. Dashboard image

- [x] 2.1 Make `front-end/next.config.ts` use `output: "standalone"` only when `NEXT_OUTPUT=standalone`; verify `npm run build` without the variable still produces no `.next/standalone`, and that `npm run lint`, `npm run typecheck` and `npm test -- --run` still pass
- [x] 2.2 Add `front-end/.dockerignore` and `front-end/Dockerfile` (deps, build with `NEXT_OUTPUT=standalone`, then a runtime stage on node:24-slim copying `.next/standalone` and `.next/static`, running as `node` on 0.0.0.0:3000 with a fetch-based HEALTHCHECK on `/` and `CMD ["node","server.js"]`, without copying `public/`); verify `docker build front-end` succeeds from a clean checkout state (no host `node_modules` or `.next` reaching the context), and that a container from it serves `/` with 200, runs as a non-zero uid, and has no `src/`, `node_modules/.cache` or `vitest` in it

## 3. Compose stack

- [x] 3.1 Add `compose.yaml` at the repo root as in design.md (build contexts, `init: true`, port variables `BACKEND_PORT` and `DASHBOARD_PORT`, `CRAWLER_API_*` passed through only when set, `CRAWLER_API_URL=http://backend:8000`, dashboard `depends_on` backend `service_healthy`); verify that `docker compose config` is valid, that `docker compose up --build --wait` ends with both services `healthy`, and that `http://localhost:3000` shows the dashboard with an empty list
- [x] 3.2 Check configurability and shutdown: run with `DASHBOARD_PORT=4000` and `CRAWLER_API_DEFAULT_MAX_PAGES=50`, then start a crawl without a page budget through `localhost:4000/api/crawls` and check its details report `max_pages` 50; then start a longer crawl and run `docker compose down`, checking that both containers exit within 10 s and not with 137 (killed)

## 4. CI smoke test

- [x] 4.1 Add `scripts/docker-smoke.sh` (bash, curl and python3 only; takes the dashboard URL as an optional argument): list crawls (200, `[]`), start a crawl of `http://dashboard:3000/` with `max_pages` 5, poll status until it's no longer running (with a timeout), expect `completed` with at least 1 page, and check both services' `id -u` isn't 0. Also add `.gitattributes` with `*.sh text eol=lf`. Verify the script passes against the running stack from 3.1 and fails with a clear message when the stack is down
- [x] 4.2 Add a `docker` job to `.github/workflows/ci.yml` (checkout, `docker compose up --build --wait --wait-timeout 180`, `bash scripts/docker-smoke.sh`, `docker compose logs` on failure, `docker compose down` always); verify the workflow parses with all four jobs and the same command sequence passes locally

## 5. Documentation

- [x] 5.1 Add a "Run everything with Docker" section to the top-level `README.md` (command, URLs, port variables, settings pass-through, stopping, Docker needs to be running) and a one-line pointer in `python/backend/README.md` and in `front-end/README.md`'s Solution section; verify every command in the section works as written against the stack

## 6. Integration check

- [x] 6.1 From a clean state (`docker compose down --rmi local`), run `docker compose up --build`, open the dashboard, start a crawl of `http://dashboard:3000/` from the form, watch it complete and browse its pages, then stop with Ctrl+C; verify that the existing checks still pass unchanged (backend: ruff, mypy, pytest; library: pytest; front-end: lint, typecheck, test, build) and that `git status` shows only the files listed in proposal.md's Impact section
