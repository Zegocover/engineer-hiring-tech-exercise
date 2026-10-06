# Daniel Refson - Web Crawler

Thanks for reviewing my test! I tried to write this like it was a real production piece of work and implement generally ( what i beleive to be) good practices to try and showcase how i would approach the problem - i didnt want to lean too heavily on already done solutions or just let AI do it for me, so i have tried to give you a real solution i would actually do as imperfect as it may be.

## AI usage

The only thing i used AI for was this readme and some research on the best patterns for web crawling complex trees as i have never made a web crawler before. I have github co-pilot ( with claude as the model) that i used to discuss the different possible approaches for the crawling algo. I also used it to generate the ASCI art because i wanted something nice in the CLI tool. To begin ( which is something i do day to day) i did take the instructions of the test and generate empty tests for me to work against to ensure I caught all the edge cases when it came to developing it.

## Quick start (requires Node.js this builds it and runs it)

```bash
npm install
npm start -- <url> [options]
```

The URL to crawl is a required argument. Anything after `--` is passed straight
through to the CLI.

```bash
npm start -- https://crawlme.zego.com/
# or, without rebuilding on every change:
npm run dev -- https://crawlme.zego.com/
```

### Options

| Flag                 | Default           | Description                                                                |
| -------------------- | ----------------- | -------------------------------------------------------------------------- |
| `--concurrency <n>`  | `5`               | Max concurrent in-flight requests                                          |
| `--max-pages <n>`    | `10000`           | Stop after crawling this many pages                                        |
| `--timeout <ms>`     | `10000`           | Per-request HTTP timeout in milliseconds                                   |
| `--user-agent <str>` | `web-crawler/1.0` | Custom `User-Agent` header sent with requests                              |
| `--json`             | off               | Print a single machine-readable JSON summary instead of a live console log |
| `-h`, `--help`       | —                 | Show usage                                                                 |

```bash
# Crawl faster, but stop after 50 pages
npm run dev -- https://crawlme.zego.com/ --concurrency 10 --max-pages 50

# Get JSON output for piping into other tools (e.g. jq)
npm run dev -- https://crawlme.zego.com/ --json > crawl-result.json
```

### Example output

```
Starting crawl: https://crawlme.zego.com/

Visited: https://crawlme.zego.com/
  Links (3):
    ↳ https://crawlme.zego.com/blog
    ↳ https://crawlme.zego.com/about
    ↳ https://crawlme.zego.com/contact

Visited: https://crawlme.zego.com/blog
  Links (1):
    ↳ https://crawlme.zego.com/blog/post-1
...

--- Crawl complete: 12 page(s) visited ---
```

## Tests

npm test # run all tests
npm run test:coverage # run with coverage report

---

## Design

### Architecture

The crawler is composed of four components, each defined as an interface with a
default implementation.

| Interface       | Default implementation             | Responsibility                                                           |
| --------------- | ---------------------------------- | ------------------------------------------------------------------------ |
| `HttpClient`    | `AxiosHttpClient`                  | Fetches HTML over HTTP(S)                                                |
| `LinkExtractor` | `CheerioLinkExtractor`             | Parses HTML and returns absolute URLs found in `<a href>` tags           |
| `Reporter`      | `ConsoleReporter` / `JsonReporter` | Handles output (live console log, or a single JSON summary via `--json`) |
| `Crawler`       | —                                  | Orchestrates the queue, visited set, and concurrency                     |

### Concurrency

Pages are processed in batches via `Promise.allSettled`. Up to `concurrency`
(default: **5**) pages are fetched in parallel. `allSettled` is used instead of
`Promise.all` so a single failing page never aborts an entire batch.089-

**Trade-off**: batching means a slow page in one batch delays the start of the
next batch. I am aware that the sliding door approach would probably be more peformant - but i dont know enough about it and didnt want to do something i didnt FULLY understand. Batching is an acceptable approach in my opinion and deals with concurrency enough.

### URL handling

- **Normalisation** — relative URLs are resolved against the page's `finalUrl`
  (the URL after any HTTP redirects). Fragment identifiers (`#section`) are
  stripped, since two URLs that differ only by fragment point to the same
  resource.
- **Deduplication** — a `Set<string>` of normalised URLs prevents re-crawling.
- **Domain scoping** — only URLs whose `hostname` exactly matches n. bv gthe starting
  URL's `hostname` are enqueued. `crawlme.zego.com` and `zego.com` are treated
  as different hosts.

### Error handling

| Scenario                    | Behaviour                                                                                                                      |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| HTTP 4xx / 5xx              | Skipped silently; page recorded with no links                                                                                  |
| Non-HTML content type       | Skipped silently; page recorded with no links                                                                                  |
| Network failure / timeout   | Reported via `Reporter.onPageError`; crawl continues                                                                           |
| Invalid start URL           | `TypeError` thrown immediately (fail fast)                                                                                     |
| Redirect to external domain | The response HTML is ignored because `content-type` is checked, and the `finalUrl` is used to resolve relative links correctly |

### Known limitations / possible extensions

- **Rate limiting** — no deliberate delay between requests. A `requestDelayMs`
  option could be added to `CrawlerOptions` for polite crawling.
- **Sitemaps** — not used for seed URLs; pages only reachable via a sitemap
  would be missed.
- **JavaScript-rendered content** — pages that load links dynamically wouldnt work for this. We would need some kind of headless browser that waits for the content to be visible and then give us the HTML.

### Is a CLI the right tool for this?

For a one-off "point it at a site and see what it finds" use case a CLI is fine and is honestly the quickest way to demo the core logic - which is what this test is really about. But if this needed to be a real product/tool that other people or systems depend on, i don't think a CLI is the best shape for it long term:

- **No persistence** - if the process dies halfway through a big crawl (laptop sleeps, terminal closes, whatever) you lose all progress and have to start again from scratch. A long running crawl really wants a job that can checkpoint the visited set/queue somewhere (even just a local sqlite file) so it can resume.

- **Single machine, single process** - the CLI is bound by the concurrency of one process on one machine. For genuinely large sites you'd want to distribute the queue (e.g. a proper message queue like SQS) so multiple workers can pull URLs off it in parallel, rather than everything being one `Promise.allSettled` batch loop.

So i'd say the CLI is the right choice for this exercise (quick to run, easy to review, no extra infra needed) but its not what i'd reach for if this had to run unattended or be relied on by other things.
