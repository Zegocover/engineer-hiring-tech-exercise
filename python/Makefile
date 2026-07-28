.PHONY: install test format lint tui cli

install:
	uv sync

test:
	uv run pytest

format:
	uv run ruff format .

lint:
	uv run ruff check .

tui:
	PYTHONPATH=src uv run python -m tui

cli:
	PYTHONPATH=src uv run python -m cli $(ARGS)
