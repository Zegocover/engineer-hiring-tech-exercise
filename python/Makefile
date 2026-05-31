.PHONY: install fix format-check lint typecheck test check run clean docker-build docker-run

ARGS ?=

install:
	uv sync

fix:
	uv run ruff format .
	uv run ruff check . --fix
	uv run ruff format .

format-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

typecheck:
	uv run ty check

test:
	uv run pytest

check: format-check lint typecheck test

run:
	uv run crawler $(ARGS)

clean:
	rm -rf .venv .pytest_cache .ruff_cache dist build *.egg-info

docker-build:
	docker build -t crawler:dev .

docker-run:
	docker run --rm crawler:dev $(ARGS)
