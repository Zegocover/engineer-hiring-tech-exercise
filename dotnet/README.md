# Zego Crawler

## The test 🧪

Create a Python app that can be run from the command line that will accept a base URL to crawl the site. For each page it finds, the script will print the URL of the page and all the URLs it finds on that page. The crawler will only process that single domain and not crawl URLs pointing to other domains or subdomains. Please employ patterns that will allow your crawler to run as quickly as possible, making full use any patterns that might boost the speed of the task, whilst not sacrificing accuracy and compute resources. Do not use tools like Scrapy or Playwright. You may use libraries for other purposes such as making HTTP requests, parsing HTML and other similar tasks.

## Running it

### Docker (recommended)

**Build:**

```bash
docker build -t zego-crawler .
```

**Run:**

```bash
docker run --rm zego-crawler https://example.com --max-connections 10
```

Or with Docker Compose:

```bash
docker compose run --rm crawler https://example.com --max-connections 10
```

Note: the image's entrypoint runs the app directly, so everything after the image name is passed straight through as its arguments — no `--` separator needed between `zego-crawler` and the URL.

### .NET SDK

Requires the [.NET SDK](https://dotnet.microsoft.com/en-us/download).

**Build:**

```bash
dotnet build src/ConsoleApp
```

**Run:**

```bash
dotnet run --project src/ConsoleApp -- https://example.com --max-connections 10
```

### Arguments

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `<uri>` | Yes | - | The absolute `http`/`https` URL to start crawling from. |
| `-m, --max-connections <maxConnections>` | No | `10` | Maximum number of concurrent page fetches. |

## Testing

### Docker

The tests spin up a real web server (via [Testcontainers](https://testcontainers.com/)) to crawl against, so the test container needs access to the host's Docker daemon through the socket:

```bash
docker build -t zego-crawler:tests --target test .
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock zego-crawler:tests
```

Or with Docker Compose (the socket mount is already wired into the `tests` service):

```bash
docker compose run --rm tests
```

### .NET SDK

```bash
dotnet test
```

This runs Testcontainers directly on the host instead of inside a container, so it depends on how your machine's own Docker CLI/daemon resolves its connection (which varies more across Windows/WSL2/Linux setups). The Docker-based path above runs the same way on every host OS, since the test container is always Linux and always talks to the daemon over `/var/run/docker.sock` regardless of what's underneath it — that's the reliable, portable option if you hit connection issues here.
