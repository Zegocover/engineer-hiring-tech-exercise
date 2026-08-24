# Development

A command-line crawler limited to a single host. Prints every page visited and the links found in each. See the [requirements](README.md#requirements) and [design](README.md#design) for details.

## Quickstart

Install:
1. Install [uv](https://docs.astral.sh/uv/) or if you have nix installed run `nix develop`.
2. Install packages using `make install`.

Then you may run the program:
```
$ uv run python -m crawler https://example.com
https://example.com/
https://example.com/about
mailto:team@example.com
```

## Checks

Formatting: `make fmt`
Test: `make test`
Typechecks: `make typecheck`
Full gate: `make check`

## Configuration

| Environment variable      | Default            | Meaning                                                     |
|---------------------------|--------------------|-------------------------------------------------------------|
| `CRAWLER_WORKERS`         | `10`               | Caps both workers and HTTP connections.                     |
| `CRAWLER_TIMEOUT_SECONDS` | `5`                | How many seconds to wait for a response.                    |
| `CRAWLER_USER_AGENT`      | `zego-crawler/0.1` | Non-empty HTTP user-agent and robots product token.         |
