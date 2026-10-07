# Design

## Context

See proposal.md for motivation. Paths below are relative to `engineer-hiring-tech-exercise/`.

`python/` is itself a project root: `python/pyproject.toml` defines the `site-crawler` package (hatchling build, ruff, mypy and pytest settings) and `python/uv.lock`. Placing `backend/` inside it nests one project in another, which matters for each tool:

| Tool | Behaviour once `python/backend/` exists |
|---|---|
| hatch sdist | Packs every file under `python/` that git doesn't ignore. An sdist built earlier contained `tests/`, `examples/` and even a stray crash dump, so it would also contain `backend/`. The wheel is safe: it is limited to `src/site_crawler`. |
| ruff | `ruff check` from `python/` discovers files recursively and lints `backend/` with backend's own `[tool.ruff]` settings, since the nearest config applies. That's a redundant second lint of the backend. |
| mypy | `files = ["src", "tests", "examples"]`, so backend files are not included. |
| pytest | `testpaths = ["tests"]` from `python/`, so backend tests are not collected. From `python/backend/`, backend's own `pyproject.toml` defines the rootdir, so the library's settings don't apply. |
| uv | `python/pyproject.toml` declares no `[tool.uv.workspace]`, so `python/backend/` stays an independent project with its own `.venv` and `uv.lock`. |

Both projects have a top-level `tests` package. Each project's pytest and mypy run from its own root, so `tests.fakes` resolves to the right one.

## Goals / Non-Goals

**Goals:**
- Run the backend from `python/backend/` with no change in behaviour, and keep all of its checks passing.
- Keep the library's sdist, lint run and tests exactly as before.

**Non-Goals:**
- A uv workspace or shared lockfile (option B, rejected in exploration in favour of independent projects).
- Any change to backend or library code, APIs or specs.

## Decisions

### 1. `git mv` the directory as a whole

`git mv backend python/backend` keeps file history (`git log --follow`). No files are renamed inside it.

### 2. Path dependency becomes `..`, and the lock is regenerated

`[tool.uv.sources] site-crawler = { path = "..", editable = true }`. `uv.lock` records the source path, so it must be regenerated with `uv lock`. CI runs `uv sync --locked`, which fails on a stale lock, so this is checked automatically.

### 3. Exclude `backend` from the library's sdist

```toml
[tool.hatch.build.targets.sdist]
exclude = ["/backend"]
```

An exclude keeps the sdist's current contents (README, tests, examples, lockfile and config) unchanged apart from the new directory. An `only-include` allow-list was considered: it's stricter, but it would change today's sdist contents as a side effect, which is out of scope for a move.

### 4. Exclude `backend` from the library's ruff run

```toml
[tool.ruff]
extend-exclude = ["backend"]
```

The backend is still linted, by its own CI job, from `python/backend/`. There, its own `pyproject.toml` is the nearest config, so the library's exclude doesn't apply.

This relies on how ruff resolves `extend-exclude` across nested configs, so the tasks verify it in both directions with `ruff check --show-files`. If excluding it from the parent also hid files when running inside the child, the fallback is to drop `extend-exclude` and make the library's lint explicit, with `ruff check src tests examples` in CI.

### 5. CI and docs

- **CI:** the `backend` job's `working-directory` becomes `python/backend`. Checkout already contains `python/`, so the `..` path dependency resolves.
- **`python/backend/README.md`:**
  - `cd backend` becomes `cd python/backend`.
  - The library link `../python/README.md` becomes `../README.md`.
  - The install-path wording `../python` becomes `..` (the parent `python/` folder).
- **`python/README.md`:** the "HTTP backend" link `../backend/` becomes `backend/`.

## Risks / Trade-offs

- [Ruff's handling of `extend-exclude` across nested configs differs from what's assumed] → Verify with `--show-files` from both directories, with the explicit-paths fallback described in decision 4.
- [Stale `.venv` or editable install pointing at the old `../python` path after the move] → Delete the moved `python/backend/.venv` before `uv sync`. It's gitignored and recreated.
- [Two `uv.lock` files under `python/` can drift (for example, different httpx versions)] → Accepted with option A. Each project is locked and tested on its own in CI. A workspace could replace this later without moving files again.
- [Open editor tabs, terminals or other changes referring to `backend/`] → The only in-flight reference, `add-crawler-dashboard`, already uses `python/backend`. Archived changes keep old paths as history.

## Migration Plan

This is a single commit in the inner repo. To roll back, revert that commit: the move is the only change, and it's a rename plus four config and doc edits.
