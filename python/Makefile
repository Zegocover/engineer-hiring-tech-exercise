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
	uv run python -m src.tui

cli:
	uv run python -m src.cli $(ARGS)
