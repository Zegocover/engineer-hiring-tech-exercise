# Tasks

Paths are relative to `engineer-hiring-tech-exercise/`.

## 1. Move the project

- [x] 1.1 Run `git mv backend python/backend`, then delete the moved, gitignored `python/backend/.venv`; verify `git status` shows only renames under `python/backend/` and no `backend/` directory remains
- [x] 1.2 In `python/backend/pyproject.toml`, change `site-crawler = { path = "../python", editable = true }` to `{ path = "..", editable = true }` and run `uv lock`; verify `uv sync --locked` succeeds from `python/backend/` and `uv run python -c "import site_crawler; print(site_crawler.__file__)"` points into `python/src/site_crawler`
- [x] 1.3 Run the backend checks from `python/backend/` (`uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, `uv run pytest`); verify all pass with the same 54 tests

## 2. Keep the library's build and lint clean

- [x] 2.1 Add `[tool.hatch.build.targets.sdist] exclude = ["/backend"]` to `python/pyproject.toml`; verify `uv build --sdist` from `python/` produces a tarball with no `backend/` entries and otherwise the same top-level contents as before (README, pyproject, uv.lock, src, tests, examples)
- [x] 2.2 Add `extend-exclude = ["backend"]` under `[tool.ruff]` in `python/pyproject.toml`; verify `uv run ruff check --show-files` from `python/` lists no `backend` files, and from `python/backend/` still lists the backend's `src` and `tests` files (if not, apply design.md decision 4's fallback)
- [x] 2.3 Run the library checks from `python/` (`uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, `uv run pytest`); verify all pass with the same 119 tests

## 3. CI and documentation

- [x] 3.1 Change the `backend` job's `working-directory` in `.github/workflows/ci.yml` to `python/backend`; verify the workflow parses and both jobs' working directories exist
- [x] 3.2 Update `python/backend/README.md` (`cd python/backend`; the library link `../README.md`; install path `..`) and the "HTTP backend" link in `python/README.md` (`backend/README.md`); verify `grep -rn "\.\./python\|\.\./backend\|cd backend" python/README.md python/backend/README.md .github` returns nothing and both link targets exist

## 4. Integration check

- [x] 4.1 From `python/backend/`, start `uv run uvicorn crawler_api.main:app`, and confirm `GET /health` returns 200 and that a `POST /crawls` against a small site completes; verify `git status` shows only the rename, the four config and doc edits, and the regenerated `python/backend/uv.lock`
