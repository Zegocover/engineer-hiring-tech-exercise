# crawler

A command-line web crawler that walks a single domain starting from a base URL and prints every page it discovers along with the links found on each page. Cross-domain and subdomain links are listed but not followed.

The original exercise brief is preserved in [`test_instructions.md`](./test_instructions.md).

## Requirements

- [`uv`](https://docs.astral.sh/uv/) (handles Python install, virtualenv, and dependency resolution)
- Python 3.13 (uv will fetch it automatically if missing)
- Optional: Docker, for running the containerised build

No system-wide `pip` or `virtualenv` is required.

## Quick start

```bash
uv sync
uv run crawler crawl https://example.com
```

Or via the Makefile, which is the canonical task interface:

```bash
make install
make run ARGS="crawl https://example.com"
```

Show all options:

```bash
uv run crawler --help
uv run crawler crawl --help
```

## Running in Docker

```bash
make docker-build
make docker-run ARGS="crawl https://example.com"
```

The image is multi-stage and runs as a non-root user. Only runtime dependencies are installed in the final layer.

## Development

| Task | Command |
| --- | --- |
| Install / sync deps | `make install` |
| Auto-fix formatting and lint | `make fix` |
| Verify everything (CI gate) | `make check` |
| Run tests only | `make test` |
| Type-check only | `make typecheck` |
| Lint only | `make lint` |

`make check` runs `format-check`, `lint`, `typecheck`, and `test` — it is non-mutating and is the gate that must pass before pushing.

`make fix` runs `ruff format`, then `ruff check --fix`, then `ruff format` again. The second format pass is intentional: the lint auto-fix can reorder imports (via the `I` rule), which can leave the file in a not-quite-formatted state.

## Design rationale

### Tooling: the Astral stack on top of `uv`

The project leans on a coherent, fast, single-vendor toolchain wherever possible:

- **`uv`** for environment and dependency management. It's an order of magnitude faster than `pip` + `venv`, resolves and locks in one step, manages the Python interpreter version, and supports PEP 735 dependency groups so dev tooling lives in `pyproject.toml` rather than a separate `requirements-dev.txt`.
- **`ruff`** for both formatting and linting. One tool, one config block, one cache — replacing the historic `black` + `isort` + `flake8` + `pyupgrade` stack with something that runs in milliseconds.
- **`ty`** for type checking. It's still pre-1.0 but is dramatically faster than `mypy` on cold runs and integrates cleanly with the same `pyproject.toml`-driven configuration.

Choosing tools from the same vendor reduces config drift and version-compatibility friction. Where `ty` is not yet stable enough for a given workflow, swapping in `mypy` would be a one-line change in the dev dependency group.

### CLI: Typer with async via `asyncer`

**Typer** was chosen over `argparse` and `click` because it derives the CLI surface directly from type hints. The function signature *is* the schema — argument names, types, defaults, and help text all come from one source — which keeps the CLI implementation small and removes a class of "schema drifted from implementation" bugs.

Typer does not natively run `async def` commands. Two clean options exist: wrap each command body in `asyncio.run(...)` manually, or use `asyncer.runnify`, a decorator from the same author as Typer and FastAPI. `runnify` was preferred because it keeps the command body genuinely `async def` (so the same function can be reused from other async contexts) and removes the boilerplate `asyncio.run` wrapper at every command.

### Concurrency model: asyncio

The crawler is I/O-bound — almost all of its time is spent waiting on HTTP responses — which is the canonical fit for `asyncio`. A thread pool would also work, but `asyncio` gives explicit, structured concurrency (`asyncio.gather`, `asyncio.Semaphore` for politeness limits, `asyncio.Queue` for work distribution) without the overhead of OS threads or the indirection of a thread pool. Using `async` from the entry point also means there is no sync/async boundary buried inside the call graph.

### Testing: pytest with `asyncio_mode = "auto"`

**pytest** is the de-facto standard and integrates with everything else here. The `pytest-asyncio` plugin is configured with `asyncio_mode = "auto"`, so any `async def test_*` function is treated as an async test automatically. This removes the per-test `@pytest.mark.asyncio` decorator noise and keeps async-by-default test code aligned with the async-by-default application code.

### Python 3.13

The newest stable Python at the time of writing. It is fully supported by uv, ruff, ty, Typer, and asyncer, and it brings meaningful improvements to error messages and the asyncio runtime. The version is pinned in `.python-version` so contributors and Docker builds resolve the same interpreter automatically.

### Packaging: `src/` layout

The application package lives under `src/crawler/` rather than at the repository root. This prevents accidental imports from the current working directory (a common source of "works on my machine" bugs where tests pass against the source tree rather than against the installed package), and it ensures the package is exercised the same way in tests, in local runs, and in the Docker image.
