# syntax=docker/dockerfile:1
# Crawler API image. Build from the python/ folder, because the backend installs the
# site-crawler library from its parent directory:
#   docker build -f python/backend/Dockerfile python

ARG PYTHON_VERSION=3.13

# --- build: resolve the locked dependencies into a virtualenv --------------------------
FROM python:${PYTHON_VERSION}-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /usr/local/bin/uv
# The venv is created where the runtime stage expects it: its scripts hard-code this path.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app
# The site-crawler library, which the backend depends on by path ("..").
COPY pyproject.toml README.md ./
COPY src ./src
# The backend itself.
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./backend/
COPY backend/src ./backend/src

# --no-editable installs both packages into the venv, so the runtime stage needs no sources.
RUN --mount=type=cache,target=/root/.cache/uv \
    cd backend && uv sync --locked --no-dev --no-editable

# --- runtime: just the virtualenv, run unprivileged ------------------------------------
FROM python:${PYTHON_VERSION}-slim
RUN useradd --system --uid 10001 --no-create-home app
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
USER app
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --start-interval=1s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

# Exec form: uvicorn receives SIGTERM directly and runs the shutdown that cancels crawls.
CMD ["uvicorn", "crawler_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
