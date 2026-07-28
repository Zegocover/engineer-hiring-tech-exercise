# Decision Log

Running log of decisions and notes made while working through this take-home exercise.


## OVERVIEW

Based on the exercise outline, as it was kept vague I've made some assumptions and will abide by those (which I think is likely the point.) the assumptions will be as follows:

- `example.com/page` counts as the same resource as `example.com/page/`
- I will be treating urchin tracking module sources as the same page e.g. `?utm_source=x` as it's there to distinguish for the website where the user is coming from. (so, not too relevant in our case)
- I will respect the ethical constraints e.g. politeness via the `robots.txt` and attempt to reduce re-crawling a website when not desired
- I will treat `<link> <script src> <img src>` or `<iframes>` tags as static content to avoid leaving the single url/domain 


### Acceptance Criteria
- Every reachable in-scope page is visited exactly once, no matter how many pages link to it
- Output for a page includes off-domain links it found, but those targets are never fetched (as per the exercise contraint)
- A cycle between two pages does not cause a hang or a repeat
- A redirect chain that leaves the domain is not followed to completion.
- A link to a large PDF or image is not downloaded in full.
- A page that never responds does not stop the crawler
- Ctrl-C produces a clean exit
- Peak concurrent connections never exceed the configured limit


## Useful commands:
>>> uv is expected to be used for this project, so the user will need to have it installed

### Setup and checks

| Command | What it does |
| --- | --- |
| `make install` | Installs dependencies into `.venv` (`uv sync`). Run this first. |
| `make test` | Runs the integration suite with pytest. |
| `make lint` | Checks the codebase with ruff. |
| `make format` | Rewrites the codebase with the ruff formatter. |

### Running the crawler

| Command | What it does |
| --- | --- |
| `make tui` | Launches the Textual UI: enter a URL, adjust workers/retries/timeout, watch progress live. |
| `make cli ARGS="<url> [flags]"` | Runs one crawl headlessly and prints the result. |

### CLI flags

Every run writes `output/<domain>.json` (one file per crawled domain, latest run wins),
then prints it. The "Wrote ..." notice goes to stderr, so stdout stays valid JSON for piping.

| Flag | Default | What it does |
| --- | --- | --- |
| `url` (positional) | — | The starting URL to crawl, e.g. `https://example.com`. |
| `--timeout` | `30` | Seconds to spend crawling overall; on expiry you get partial results with `completed: false`. |
| `--max-concurrent-requests` | `10` | Cap on in-flight requests, and on the HTTP connection pool. |
| `--output-dir` | `output` | Where the per-domain JSON is written. |
| `--pretty` | off | Prints the grouped human-readable summary instead of the raw JSON. |
| `--verbose` / `-v` | off | Logs each page as it is fetched, plus robots.txt decisions. |

### Examples

```bash
# Smallest useful run: crawl and write output/example.com.json
make cli ARGS="https://example.com"

# Human-readable summary, short leash, with per-page progress logging
make cli ARGS="https://harryhallows.github.io/portfolio/ --timeout 5 --pretty -v"

# Gentle on the target: 2 workers, 60s budget
make cli ARGS="https://example.com --max-concurrent-requests 2 --timeout 60"

# Pipe the JSON straight into jq. `-s` stops make echoing the recipe into
# stdout; stderr carries the "Wrote ..." notice, so what's left is valid JSON.
make -s cli ARGS="https://example.com" 2>/dev/null | jq '.found_urls_by_domain | keys'

# Send results somewhere other than ./output
make cli ARGS="https://example.com --output-dir ./runs"
```

## IMPLEMENTATION

### Pre-work

I started by curling my portfolio website, as I know it reliably contains links outside of it's "domain" e.g. links to my socials and github, to verify a rough expected HTML response with a variety of the common issues to avoid. 

This will be useful later on when I need to parse the resposne data into buckets of data. 

I spent some time thinking about how a crawler works in reality on a functional level. Got together some rough thoughts and then did some research into how companies build crawlers and looked at `https://scrape.do/blog/web-crawler-python/` and `https://www.hellointerview.com/learn/system-design/problem-breakdowns/web-crawler` to one, align my assumptions with engineering companies specialising in that space (specifically `scrap.do`, ). 

NOTE: it was nice to see that I was reasonably aligned with the given approach for what was in my head. 

which was the following key things:
- fetch a url
- parse the html
- traverse additional links
- consider ethical issues (e.g. robots.txt very common on most sites)
- consider failure e.g. cloudflare firewall (I validated this against zego.com)
- scalability / ethical considerations, if I were to proceed past a single url on a single instance, how do I ensure multi-threaded spiders don't hit the same url twice. (Maybe some form of redis cache check, and a TTL?)

```bash
Simple Curl:
curl zego.com

Response:
<html>
<head><title>301 Moved Permanently</title></head>
<body>
<center><h1>301 Moved Permanently</h1></center>
<hr><center>cloudflare</center>
</body>
</html>
```

NOTE: I also thought, surely there's a crawler test site (there has to be, and there is! https://crawler-test.com/)


### Test driven process (my process :) )

I started by outlining the specific Acceptance Criteria (ACs) for my crawler (see above). I usually subscribe to the TDD approach, as it allows me to validate my logic based on those ACs. This also ensures me that the edgecases i've built are doing as intended, not introducing any strange behaviour. (Granted this is reliant that I capture all edgecases to be full proof.) 

I first started by building the "infrastructure" to help enable my testing, by getting claude to help build out a quick fixture to produce an adequate dynamic testing app to call my tests against. (see: `tests/integrations/helpers/website.py`)

I then built out the test suite with claude to help do RED GREEN REFACTOR, focusing initially on the crawler as that was where most of my logic was primarily hosted (included the searching at the beginning)

When I had those operational, I went back and extracted out the BFS (search.py) logic to it's own module to follow single responsibility principles. 

Afterwards I started looking into how to extract and process robots.txt files starting with [link](https://datatracker.ietf.org/doc/rfc9309/) afterwards, I queried gemini, to get a bit of a more practical understanding of how to extract the robot.txt and specifically if my understanding was correct (some basic logical validation)

Then I built out some basic tests initially around the different status code behaviours then I started to build out the RobotCache to handle validating the robot.txt and caching the results to avoid re-hitting the same endpoints for the same urls.

After getting a more concrete structure, I went back and added additional edge cases around verifying the cache itself (I had forgotten this edgecase).

Which is the advantage of RED GREEN REFACTOR :)

Other than adding test cases which I thought of when validating the overall application logic, e.g. how my initial searching was missing out external urls and only the domain specific ones were extracted. (close one!)

additionally I was utilising [crawler-test](https://crawler-test.com/) to stress test my runs

```bash
make cli ARGS="https://harryhallows.github.io/portfolio/ --timeout 5 --pretty"
PYTHONPATH=src uv run python -m cli https://harryhallows.github.io/portfolio/ --timeout 5 --pretty
Crawl completed — 4 page(s) visited

Visited (4):
  - https://harryhallows.github.io/
  - https://harryhallows.github.io/cv.pdf
  - https://harryhallows.github.io/portfolio
  - https://harryhallows.github.io/portfolio/

Found URLs by domain (6 domain(s)):
  github.com (1):
    - https://github.com/HarryHallows
  githubstatus.com (1):
    - https://githubstatus.com
  harryhallows.github.io (4):
    - https://harryhallows.github.io/
    - https://harryhallows.github.io/cv.pdf
    - https://harryhallows.github.io/portfolio
    - https://harryhallows.github.io/portfolio/
  help.github.com (1):
    - https://help.github.com/pages/
  twitter.com (1):
    - https://twitter.com/githubstatus
  www.linkedin.com (1):
    - https://www.linkedin.com/in/harryhallows/
```


## CHOICES

### URL normalisation

Collapse URL spellings that mean the same resource (trailing slash, tracking params,
fragments, host case) before deciding what to fetch, so "visited exactly once" actually
holds. Applied to traversal only: reporting keeps the link as the page wrote it. Lives
in `UrlNormaliser` alongside the search, because it exists to serve traversal.

### Fail closed when robots.txt can't be retrieved

If robots.txt is unreachable (5xx, 401/403, redirect loop) the crawl refuses to start,
because an empty ruleset parses as *allow everything*, so the naive error path would
grant an outaged site more access than a healthy one. Costs me a flaky site entirely,
which is the right side to err on.

### Non-`text/plain` 200 treated as 404

Stricter than RFC 9309, which doesn't mandate a content type. Sites commonly serve an
HTML error page with a 200 for a missing robots.txt, and parsing that yields junk
directives that then silently govern the crawl.

### BFS over DFS

Explores by distance from the start, so shallow high-value pages come first and a
timed-out run still has the useful ones. It also fits a work queue naturally, which is
what makes the concurrency model below simple.

### Fixed worker pool, not `asyncio.gather` over everything

Recursively gathering every link has no ceiling: one page with 500 links opens 500
connections. A queue plus a fixed number of workers caps in-flight requests by
construction rather than by hope, and the connection pool is sized to match.

### Lock-free `visited` set

No lock, because there's no `await` between the membership check and the add, and
asyncio only switches tasks at suspension points. Single-process reasoning only, and
commented in code since it reads like a bug and quietly breaks if someone adds an
`await` in the middle.

### Retry on 429 and 5xx only

Transient faults are worth retrying; a 404 will still be a 404 and hammering it is rude.
Exponential backoff with jitter so workers rejected together don't retry in lockstep,
and the server's `Retry-After` wins over my own guess when it sends one.

### httpx over aiohttp or requests

`requests` is synchronous, which rules it out. httpx won on testability: its ASGI and
mock transports let the whole suite run in-process with no network. One client is built
at the entry point and injected down, so there's a single pool, a single owner, and one
`User-Agent` across robots.txt and page fetches.

### stdlib HTMLParser over BeautifulSoup

Enough for pulling `href`s, with no dependency, and it ignores markup inside HTML
comments for free. BeautifulSoup would only pay off on badly broken markup.

### Output: one JSON file per crawled domain

Stands in for a datastore. Serialisation lives in one module so the CLI and TUI can't
drift into emitting different documents, and results are sorted so two runs of a site
diff cleanly.

### TUI

Makes the reviewer's life, and mine, slightly easier. And it's fun.

## AI USAGE

I primarily used AI to help provision and build utilities, for the repo to enable devX improvements, whether that's spinning up n Makedown commands to help navigate the repo commands.
Essentially I will leverage claude to help setup the belts and braces that I would expect as a minimum to be in a working production project. (With the caveat of time of course.)


Additionally, I will use AI to help wade through boiler plate specifics, e.g. with testing configs and getting appropriate testing configured in a timely manner. as well as utilising AI to help validate ad-hoc learnings and research as I haven't built a crawler before and wanted to be sure I was adhearing to best practices, and ensure I had the correct understanding to do so. 

---


## Improvements

Known gaps, in the order I'd close them:

- Stream responses, check content-type/length on headers, so large files aren't buffered
- URL normalisation before `can_fetch`, so robots matching and dedup use the same string
- Handle `KeyboardInterrupt` and flush partial results
- Abort off-domain redirects at the hook rather than fetching the landing page

Beyond that: `.pre-commit`; a real datastore instead of JSON files; unit layering for the
retry policy and link extractor; metrics (runtime, pages/sec); and a persistent frontier
with shared `visited` (Redis + TTL) so the crawl can distribute across instances.