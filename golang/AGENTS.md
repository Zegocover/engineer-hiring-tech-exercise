# Repository Guidelines

## Project Structure & Module Organization

This directory contains the Go crawler exercise, using module `zego.com/engineer-hiring-tech-exercise`. `cmd/cli/crawler.go` holds the command-line entry point and `Run` function. `internal/client/client.go` contains the HTTP client wrapper. Keep reusable crawler logic under `internal/` and CLI argument handling under `cmd/cli/`.

`README.md` contains the requirements and submission instructions. `docs/arch.md` and `docs/TODO` capture architecture notes and planned features.

## Coding Style & Naming Conventions

Use standard Go formatting, including tabs supplied by `gofmt`. Keep package names short and lowercase, exported identifiers in PascalCase, and unexported identifiers in camelCase. Use idiomatic initialisms such as `URL` and `HTTP`. Propagate contextual errors and keep process exits in the CLI layer.

## Testing Guidelines

Always use table-driven tests, with named test cases executed as subtests using `t.Run`.

Use Go’s `testing` package and `net/http/httptest` for deterministic local HTTP fixtures. Name files `*_test.go` and tests `TestBehavior`. Cover URL resolution, duplicate suppression, cycles, hostname boundaries, redirects, failures, and cancellation. Exercise worker limits with race detection. No coverage threshold is configured; prioritize meaningful behavior tests over a percentage.

## Commit & Pull Request Guidelines

Recent history mixes descriptive subjects with prefixes such as `docs:`; no strict convention is established. Use concise, imperative subjects. PRs should explain behavior changes, design trade-offs, and validation results, linking relevant issues. Document development and AI tooling in the README as requested by the exercise.

## Crawler Design Constraints

Restrict fetching to the seed hostname, including redirects; exclude other domains and subdomains. Bound concurrency, reuse HTTP connections, and deduplicate scheduled URLs. Report discovered external links without crawling them. Do not use Scrapy or Playwright.
