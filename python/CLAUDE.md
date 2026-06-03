# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Zego take-home hiring exercise: a single-domain web crawler CLI named `crawler`. The exercise is judged on software design, code structure, and testing — not just a working result — and the `python/README.md` is expected to carry a written discussion of design decisions and trade-offs. The original brief is in `test_instructions.md`.

**Current state: fully implemented** on branch `zegotest` (not yet merged to `main`); `make check` is green. `crawler crawl URL` crawls a single domain concurrently and prints each page with the links found on it. The full design discussion and trade-offs live in `python/README.md`.

### Constraints from the brief (these shape the real implementation)

- Crawl **one domain only** — links to other domains *and subdomains* must be listed but **not followed**.
- **Do not use Scrapy or Playwright.** Libraries for HTTP, HTML parsing, etc. are fine.
- Speed matters: the crawler should use concurrency to run fast without sacrificing accuracy or wasting compute.

## Commands

The `Makefile` is the canonical task interface; run everything from the `python/` directory.

| Task | Command |
| --- | --- |
| Install / sync deps | `make install` (= `uv sync`) |
| **CI gate — run before pushing** | `make check` |
| Auto-fix formatting + lint | `make fix` |
| Tests | `make test` (= `uv run pytest`) |
| Single test | `uv run pytest tests/test_cli.py::test_help_lists_crawl_command -v` or `uv run pytest -k <pattern>` |
| Type-check | `make typecheck` (= `uv run ty check`) |
| Lint | `make lint` (= `uv run ruff check .`) |
| Run the CLI | `make run ARGS="crawl https://example.com"` |
| Docker build / run | `make docker-build` · `make docker-run ARGS="--help"` |

- **`make check`** runs `format-check`, `lint`, `typecheck`, `test` in sequence. It is non-mutating and is the gate that must pass before pushing.
- **`make fix`** runs `ruff format` → `ruff check --fix` → `ruff format` again. The second format pass is **intentional**: the lint auto-fix can reorder imports (ruff `I` rule), leaving the file not-quite-formatted. Don't "simplify" it to a single format.

## Architecture

The code is a Clean Architecture split, with dependencies pointing inward to a pure domain core:

- **`src/crawler`** (outer layer / composition root) — the Typer app (`cli.py`), the `crawler_factory` wiring (`factory.py`), and the text/JSONL renderers (`presenters.py`).
- **`src/domains/crawler`** (pure core, no I/O) — the async `engine.py` coordinator; `parser.py`, holding `SelectolaxExtractor` + `LinkParser` (HTML link extraction and on-host/off-site classification); `ports.py`, with the only two ports — the `Fetcher` and `Queue` Protocols; frozen `models.py`; and `urls.py`. `tests/test_architecture.py` AST-scans this package and fails if it imports an I/O or framework library (httpx, typer, asyncer) or an outer layer (`crawler`, `gateways`); pure selectolax is allowed.
- **`src/gateways`** (adapters implementing the ports) — `http/httpx_fetcher.py` (`HttpxFetcher`) and `queue/in_memory.py` (`InMemoryQueue`).
- **Concurrency model** — N fetch workers pull URLs from a `pending` queue and push responses to a `fetched` queue; a single parse loop owns the visited set and in-flight counter, so no locks are needed. The crawl is complete when the in-flight counter reaches zero.

- **`src/` layout.** Tests live in `tests/` (outside the package, so they aren't shipped in wheels). The `src/` layout is deliberate — it prevents accidental imports from cwd so tests exercise the installed package, not the source tree.
- **Two entry points**, both routing to the same Typer app (`crawler.cli:app`): the `crawler` console script (defined in `[project.scripts]`) and `python -m crawler` (via `__main__.py`).
- **CLI = Typer.** The function signature *is* the schema (arg names, types, defaults, help all derive from type hints). Add new commands as functions decorated with `@app.command()`.
- **Async commands via `asyncer.runnify`.** Command bodies are real `async def`; `@runnify` wraps them so Typer can call them synchronously. **`@runnify` must be the innermost decorator, directly below `@app.command()`** — otherwise `typer.Exit` gets swallowed and exit codes are wrong. The concurrency model is `asyncio` (the work is I/O-bound) — see the Architecture section above for the fetch-workers/parse-loop design.
- **Tests use pytest with `asyncio_mode = "auto"`** — any `async def test_*` runs as an async test with no per-test marker. CLI behaviour is tested through Typer's `CliRunner`.

## Toolchain (the Astral stack on `uv`)

Python **3.13**, pinned in `.python-version` (uv auto-fetches it). Everything is driven through `uv` — there is no system `pip`/`virtualenv`.

- **`uv`** — env, deps, interpreter, lockfile. Dev tools live in a PEP 735 `[dependency-groups]` block (not a `requirements-dev.txt`); `uv sync` installs them, `uv sync --no-dev` is runtime-only (used in the Docker builder stage).
- **`ruff`** — format + lint in one tool. Config: line-length 100, lint rules `E, F, I, UP, B, SIM`.
- **`ty`** — type checker, **pre-1.0**. Config lives in `[tool.ty.environment]` (`root = ["./src"]`) in `pyproject.toml`. ty's config keys are still changing — if a `ty` upgrade breaks, that block is where to fix it. Swapping ty for mypy would be a one-line dev-dependency change.

## Docker

Multi-stage, uv-based, runs as a **non-root** user (uid 1001). The runtime stage installs only runtime deps and uses `uv sync --no-editable`, so the package is installed into the venv and `src/` is **not** copied into the final image. Base images are pinned by SHA digest — when bumping them, update both the builder and runtime digests.

## Design docs

`docs/superpowers/specs/` and `docs/superpowers/plans/` hold the design spec and the step-by-step scaffolding plan. Where those docs disagree with the code (e.g. the spec shows `[tool.ty.src]` and a `src`-copying Dockerfile), **the code is the source of truth** — the config was tightened after the docs were written.
