# Proposal

## Why

The brief points reviewers to the `python/` folder for the Python exercise, but the FastAPI backend currently sits beside it in `backend/`, which is easy to miss. Moving the backend into `python/` puts the whole Python solution (library, CLI and HTTP API) in the folder reviewers are told to open. It also frees the top level for the Next.js dashboard planned in `add-crawler-dashboard`, which lives in `front-end/`.

## What Changes

- Move `backend/` to `python/backend/` with its history (`git mv`). It stays an independent uv project with its own `pyproject.toml` and `uv.lock`, not a uv workspace member.
- Change the backend's path dependency from `site-crawler = { path = "../python" }` to `{ path = ".." }` and regenerate `python/backend/uv.lock`.
- Keep the library's build and tooling free of the nested project:
  - Restrict the `site-crawler` sdist to the library's own files, so `python/backend/` is not shipped inside `site_crawler-*.tar.gz`. The wheel is already limited to `src/site_crawler`.
  - Exclude `backend/` from the library's ruff run, so it isn't linted twice (once with each project's config).
- Update the CI `backend` job's `working-directory` to `python/backend`.
- Fix the paths in `python/backend/README.md` (library link and install path) and in `python/README.md`'s "HTTP backend" section.
- No code, API or behaviour changes in either project.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This only relocates the backend project and adjusts build, CI and documentation paths; no requirement in `site-crawl`, `crawler-extension-api` or `crawl-api` changes. The change will set `skip_specs: true`.

## Impact

- **Moved**: `backend/` becomes `python/backend/` (source, tests, `pyproject.toml`, `uv.lock`, README).
- **Library config**: `python/pyproject.toml` gains an sdist include list and a ruff `extend-exclude`.
- **CI**: `.github/workflows/ci.yml`, backend job working directory.
- **Docs**: `python/README.md` and `python/backend/README.md` links and commands.
- **Developers**: the backend now runs from `python/backend` (`cd python/backend && uv run uvicorn crawler_api.main:app`).
- **Ordering**: land this before `add-crawler-dashboard`, whose route handlers and docs refer to the backend's new location.
