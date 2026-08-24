.DEFAULT_GOAL := check
.PHONY: install fmt lint typecheck test check

# The Nix devShell overrides RUFF with the nixpkgs binary (the PyPI wheel can't
# run on NixOS). Elsewhere, the uv-managed wheel is used.
RUFF ?= uv run ruff

install: ## Sync .venv with runtime + dev dependencies.
	uv sync

fmt: ## Auto-format.
	$(RUFF) format .
	$(RUFF) check --fix .

lint: ## Lint (no writes).
	$(RUFF) format --check .
	$(RUFF) check .

typecheck: ## Static type check.
	uv run mypy

test: ## Run the test suite.
	uv run pytest

check: lint typecheck test ## Full CI gate.
