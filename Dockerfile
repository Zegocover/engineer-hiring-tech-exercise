# Image a Kubernetes worker would run. The crawl URL is passed at start.
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

ENTRYPOINT ["site-crawler"]
