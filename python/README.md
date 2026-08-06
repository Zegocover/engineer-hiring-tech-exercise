# python-developer-test

# Zego

## About Us

At Zego, we understand that traditional motor insurance holds good drivers back.
It's too complicated, too expensive, and it doesn't reflect how well you actually drive.
Since 2016, we have been on a mission to change that by offering the lowest priced insurance for good drivers.

From van drivers and gig economy workers to everyday car drivers, our customers are the driving force behind everything we do. We've sold tens of millions of policies and raised over $200 million in funding. And we’re only just getting started.

## Our Values

Zego is thoroughly committed to our values, which are the essence of our culture. Our values defined everything we do and how we do it.
They are the foundation of our company and the guiding principles for our employees. Our values are:

<table>
    <tr><td><img src="../doc/assets/blaze_a_trail.png?raw=true" alt="Blaze a trail" width=50></td><td><b>Blaze a trail</b></td><td>Emphasize curiosity and creativity to disrupt the industry through experimentation and evolution.</td></tr>
    <tr><td><img src="../doc/assets/drive_to_win.png?raw=true" alt="Drive to win" width=50></td><td><b>Drive to win</b></td><td>Strive for excellence by working smart, maintaining well-being, and fostering a safe, productive environment.</td></tr>
    <tr><td><img src="../doc/assets/take_the_wheel.png?raw=true" alt="Take the wheel" width=50></td><td><b>Take the wheel</b></td><td>Encourage ownership and trust, empowering individuals to fulfil commitments and prioritize customers.</td></tr>
    <tr><td><img src="../doc/assets/zego_before_ego.png?raw=true" alt="Zego before ego" width=50></td><td><b>Zego before ego</b></td><td>Promote unity by working as one team, celebrating diversity, and appreciating each individual's uniqueness.</td></tr>
</table>

## The Engineering Team

Zego puts technology first in its mission to define the future of the insurance industry.
By focusing on our customers' needs we're building the flexible and sustainable insurance products
and services that they deserve. And we do that by empowering a diverse, resourceful, and creative
team of engineers that thrive on challenge and innovation.

### How We Work

- **Collaboration & Knowledge Sharing** - Engineers at Zego work closely with cross-functional teams to gather requirements,
  deliver well-structured solutions, and contribute to code reviews to ensure high-quality output.
- **Problem Solving & Innovation** - We encourage analytical thinking and a proactive approach to tackling complex
  problems. Engineers are expected to contribute to discussions around optimization, scalability, and performance.
- **Continuous Learning & Growth** - At Zego, we provide engineers with abundant opportunities to learn, experiment and
  advance. We positively encourage the use of AI in our solutions as well as harnessing AI-powered tools to automate
  workflows, boost productivity and accelerate innovation. You'll have our full support to refine your skills, stay
  ahead of best practices and explore the latest technologies that drive our products and services forward.
- **Ownership & Accountability** - Our team members take ownership of their work, ensuring that solutions are reliable,
  scalable, and aligned with business needs. We trust our engineers to take initiative and drive meaningful progress.

## Who should be taking this test?

This test has been created for all levels of developer, Junior through to Staff Engineer and everyone in between.
Ideally you have hands-on experience developing Python solutions using Object Oriented Programming methodologies in a commercial setting. You have good problem-solving abilities, a passion for writing clean and generally produce efficient, maintainable scaleable code.

## The test 🧪

Create a Python app that can be run from the command line that will accept a base URL to crawl the site.
For each page it finds, the script will print the URL of the page and all the URLs it finds on that page.
The crawler will only process that single domain and not crawl URLs pointing to other domains or subdomains.
Please employ patterns that will allow your crawler to run as quickly as possible, making full use any
patterns that might boost the speed of the task, whilst not sacrificing accuracy and compute resources.
Do not use tools like Scrapy or Playwright. You may use libraries for other purposes such as making HTTP requests, parsing HTML and other similar tasks.

## The objective

This exercise is intended to allow you to demonstrate how you design software and write good quality code.
We will look at how you have structured your code and how you test it. We want to understand how you have gone about
solving this problem, what tools you used to become familiar with the subject matter and what tools you used to
produce the code and verify your work. Please include detailed information about your IDE, the use of any
interactive AI (such as Copilot) as well as any other AI tools that form part of your workflow.

You might also consider how you would extend your code to handle more complex scenarios, such a crawling
multiple domains at once, thinking about how a command line interface might not be best suited for this purpose
and what alternatives might be more suitable. Also, feel free to set the repo up as you would a production project.

Extend this README to include a detailed discussion about your design decisions, the options you considered and
the trade-offs you made during the development process, and aspects you might have addressed or refined if not constrained by time.

# Instructions

1. Create a repo.
2. Tackle the test.
3. Push the code back.
4. Add us (@nktori, @danyal-zego, @bogdangoie, @cypherlou, @marliechiller and @ZEGODiogoAlves) as collaborators and tag us to review.
5. Notify your TA so they can chase the reviewers.

---

# The Solution 🐕

## What does it do? (explained for a child, or a very good golden retriever)
```
This why we aim that the explanation be a simple as possible we extract this from the  2011 movie Margin Call, 
CEO John Tuld (played by Jeremy Irons) tells a young risk analyst to explain a catastrophic financial crisis by saying,
"Speak as you might to a young child or a golden retriever. It wasn't brains that got me here, I can assure you of that."
```

Imagine a website is a big park, and every page is a lamppost.

You are a very good dog. Your human says: "start at this lamppost." You run
to it, sniff it, and find little signs pointing to other lampposts. You bark
out loud what you found ("this lamppost points to these ones!"), then you run
to each new lamppost and do it again.

The rules of being a good dog:

- **Stay in your park.** Some signs point to other parks (other websites).
  You bark about them, but you never leave your park.
- **Don't sniff the same lamppost twice.** You remember every lamppost
  you've seen. Sniffed it once? Done. Move on.
- **You are actually ten dogs.** Ten of you sniff ten different lampposts at
  the same time, so the whole park gets sniffed really fast.
- **If a lamppost is busy, wait and come back.** First you wait a little.
  Still busy? Wait twice as long. Then twice as long again. You never sit
  there barking at a busy lamppost non-stop. That's rude.
- **If the park has rules on the gate, follow them.** The gate sign
  (`robots.txt`) says which lampposts dogs aren't allowed to sniff. Good
  dogs read the gate sign.
- **If a lamppost asks "are you a human?", you leave.** You are a dog. You
  do not lie about being a dog. You note it down and walk away.
- **Go home when you're tired.** After enough lampposts (`--max-pages`),
  you stop, so you never run forever.

That's it. That's the whole program. Everything below is the grown-up
version of the same sentences.

## How to run it

```bash
cd python
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python crawler.py https://example.com
```

Useful flags:

| Flag | What it does | Default |
|---|---|---|
| `--concurrency N` | how many pages to fetch in parallel | 10 |
| `--max-pages N` | hard stop after N pages | 1000 |
| `-v` | log skipped/failed URLs to stderr | off |
| `--no-robots` | ignore robots.txt (please don't) | off |

Run the tests:

```bash
.venv/bin/python -m pytest tests/ -q
```

## Design decisions and trade-offs

**One file, three responsibilities.** `crawler.py` holds a `Fetcher` (HTTP +
retries), a pure `extract_links()` function (HTML → URLs), and a `Crawler`
(queue + workers + scope rules). Each piece has a single responsibility and
is injected into the next (the `Crawler` receives a `Fetcher`; output goes
through an injectable `out` callable), so every piece is testable in
isolation. That is the useful core of SOLID without the ceremony of
one-class-per-file and interfaces with a single implementation. For a
~250-line program, a package structure would be bureaucracy, not
architecture. If the program grows, each of these three pieces can be
lifted into its own module without rewriting anything, because they
already only talk to each other through their constructors.

**Concurrency: `asyncio`, not threads or processes.** Crawling is almost
pure I/O-wait: network round-trips dominate, parsing is cheap. That is
exactly the workload async is built for: one event loop, N worker tasks
pulling from a shared `asyncio.Queue`, thousands of concurrent sockets
possible at near-zero memory cost. Threads would work but pay
per-thread overhead and need locks around the shared `seen` set;
multiprocessing buys CPU parallelism we don't need and IPC costs we do.
(If parsing ever became the bottleneck, a process pool just for parsing
would be the surgical fix.)

**The dedup pattern, in simple words.** There is one to-do list (the
`asyncio.Queue`) and one memory of everything ever added to it (the `seen`
set). The set is the *memory*, and the `_enqueue` method is the *doorman*
that consults it. Before a URL goes on the to-do list, the doorman checks
the memory: already there? Skip it. Not there? Remember it *and* add it to
the list, in one step. Because the check happens *before* adding (not
before fetching), a URL can never sneak onto the list twice, even with ten
workers running. And because asyncio runs one piece of code at a time
(workers take turns on a single event loop rather than truly running
simultaneously), those two steps can't be interrupted halfway, so no locks
are needed at all. (Dedup is by discovered URL, not by final URL: two
links that redirect to the same page are each fetched once; content-hash
dedup is listed under future work.)

**Libraries: `httpx` + `beautifulsoup4`, both open source, nothing else.**
The brief forbids Scrapy/Playwright, and honestly they'd be overkill anyway.
`httpx` gives async HTTP, connection pooling, timeouts and redirect handling
in one battle-tested client; BeautifulSoup is the boring, robust choice for
messy real-world HTML. Everything else is the standard library: CLI
(`argparse`), URL handling (`urllib.parse`), robots.txt
(`urllib.robotparser`), and retries/backoff (a dozen lines). I considered `tenacity` for
retries and `lxml`/`selectolax` for faster parsing; both were rejected as
dependencies that replace a few readable lines (retry loop) or optimise a
non-bottleneck (parsing).

**Scope rule: exact host match.** The brief says no other domains *and* no
subdomains, so scope is `parsed.netloc == base.netloc`, nothing cleverer.
External and subdomain links are still *printed* (the brief asks for every
URL found on a page); they're just never *fetched*. Off-domain redirects are
also caught: redirects are followed, so the redirected response is
downloaded, but if it landed off-host it is discarded (never parsed, never
enqueued), so a redirect can't smuggle the crawler out of the park. One
special case: if the *base URL itself* redirects off-host (the classic
apex to `www.` redirect; `www.` is a subdomain, so it's out of scope by
the brief's rules), there is nothing to crawl; instead of exiting silently,
the crawler prints an error telling you to re-run with the redirect target.

**Failure handling: one page failing must never kill the crawl.** Every
per-URL problem funnels into a single `FetchError` that the worker logs and
skips. Specifically:

- **Network errors and 5xx/429** → retried up to 3 times with *jittered
  exponential backoff* (0.5s, 1s, 2s… doubling towards a 30s cap, plus up to
  0.5s of random jitter on top so concurrent workers don't retry in lockstep
  and re-DDoS the site).
- **Rate limiting (429)** → if the server sends an integer `Retry-After`, we
  honour it and wait at least that long: the server knows its limits better
  than we do. (The rarer HTTP-date form of `Retry-After` falls back to
  normal backoff.)
- **Captcha / anti-bot walls (Cloudflare and friends)** → detected by
  status + body markers and abandoned *immediately, with zero retries*.
  Deliberate decision: a crawler that retries or evades captchas is being a
  bad citizen (and usually breaking the site's terms of service). We detect,
  log, and walk away. The same ethic drives the honest User-Agent and
  robots.txt support: the sustainable answer to anti-scraping measures is
  politeness, not an arms race.
- **Locked-down robots.txt (401/403)** → treated as "deny everything",
  matching the stdlib parser's own semantics: if a site hides its rules,
  we assume we're not welcome.
- **Non-HTML content, 404s, malformed URLs, `mailto:`/`javascript:` links,
  duplicate links, fragment-only variants** → all filtered or skipped
  quietly (visible with `-v`).
- **Bounded by design:** per-request timeouts (10s connect/read/write),
  bounded retries, bounded concurrency, bounded page count. Two known
  limits, on purpose: the read timeout is per-chunk rather than
  whole-request, and response bodies are buffered in full, so a
  deliberately hostile server could drip-feed bytes or serve an enormous
  page. Whole-request deadlines and body-size caps are the first
  production-hardening step (see future work); for a data-engineering eye,
  knowing exactly where your bounds end is the difference between a script
  and a pipeline component.

Is this fail-fast? Mostly the opposite. There are three different failure
philosophies here, each picked for its spot:

- **Fail-soft in the middle of the work.** Fail-soft means: when a part
  breaks, the system keeps working, just with less (also called "graceful
  degradation"). One broken page is logged and skipped, so a crawl of
  1000 pages doesn't die because page 47 is broken: you get 999 pages
  and a log line instead of nothing.
- **Fail-fast at the boundaries.** A bad base URL kills the program
  immediately at the CLI, and a base URL that redirects off-host prints a
  loud error instead of silently finishing with empty output. Bad input
  should be rejected loudly and early, not half-processed.
- **Fail-safe on the ethical line.** Fail-safe is different from
  fail-soft: it means failing in a way that *causes no harm*, even if
  that means stopping entirely (like an elevator brake clamping shut when
  power fails). A captcha wall abandons that URL instantly with zero
  retries: the harmless behaviour toward the website is to walk away,
  not to keep trying.

**Testing: TDD workflow, BDD naming, zero real network.** The suite (17
tests) is written as behaviour specifications (for example
`test_given_a_captcha_wall_when_fetching_then_it_gives_up_without_retrying`),
so the test list reads as the product's rulebook. Tests were written
against the behaviours first and drove the design (the injectable `sleep`
and `out` parameters exist because the tests demanded observable backoff
and output). All HTTP goes through `httpx.MockTransport`, a fake site
defined as a dict of routes, so the suite is deterministic, offline, and
runs in well under a second. I chose plain pytest with Given/When/Then
names over `pytest-bdd`/Gherkin: same behavioural clarity, one less
dependency and indirection layer.

## Tools used

- **IDE:** PyCharm.
- **AI:** a terminal-based AI coding assistant for pair-writing the
  implementation and tests against my design constraints (async worker
  pool, exact-host scope, backoff-with-jitter, no captcha evasion), plus
  reviewing edge cases. All code was run, linted (`ruff`) and tested locally
  before commit. To guard against AI hallucination, a second *independent*
  AI review agent (a different model from the one that wrote the code) then
  adversarially verified the result: it re-ran the tests, checked every
  claim in this README against the source, and probed the library APIs for
  invented parameters. It confirmed no hallucinated APIs and caught three
  overclaims in an earlier draft of this section (redirect-alias dedup,
  `Retry-After` date form, absolute "can't hang" wording), which were then
  fixed, following standard hallucination-reduction practice (grounding,
  verification, cross-model checking).
- **Quality gates:** `pytest`, `ruff check`, `ruff format`.

## How I'd extend it (and why the CLI stops being the right shape)

The brief is right that a CLI doesn't scale to crawling many domains at
once. The current design is already split into the pieces the production
version would need:

1. **Crawl state moves out of memory.** Today the `seen` set and the queue
   live in the process's memory, so a crash loses everything. In
   production, both move together into one external store (Redis *or*
   Postgres; either can hold both); the crawler becomes a stateless
   worker. Crawls survive restarts and can be resumed. At very large
   scale, exact dedup gives way to a Bloom filter.
2. **CLI → service.** A small API (or just a job queue: SQS/Pub/Sub +
   workers) where you *submit* crawl jobs and *fetch* results, instead of
   watching stdout. Results land in object storage or a table (page URL,
   link, crawl id, fetched-at), at which point this is a normal data
   pipeline: idempotent workers, checkpointed state, queryable output.
3. **Per-host politeness.** Multi-domain crawling needs per-host rate
   limits and per-host robots caches, not one global semaphore; the
   current single-host assumption is the main thing that changes.
4. **Observability.** Structured logs already exist; production adds
   metrics (pages/sec, error rates by class, queue depth) and alerting.
   For example: Prometheus to collect the numbers with Grafana to
   dashboard them (the standard open-source pair), or Datadog as the
   one-stop commercial alternative, with alerts through Alertmanager or
   PagerDuty.
5. **Nice-to-haves I cut for time:**
   - *Honouring robots.txt `Crawl-delay`*: some sites' robots.txt says
     "wait N seconds between requests". The crawler obeys the
     allow/disallow rules but ignores this delay number; honouring it
     would mean pausing between fetches to the same site.
   - *sitemap.xml seeding*: many sites publish a file listing all their
     pages. Reading it first would give the full page list up front,
     instead of discovering pages only by following links (which misses
     pages nothing links to).
   - *Streaming HTML parsing*: today a page is downloaded whole into
     memory, then parsed. Streaming means parsing bytes as they arrive,
     so a 500 MB page can't blow up memory.
   - *Retry budgets per host*: today each URL gets 3 retries
     independently, so if a site is down, 100 URLs × 3 retries = 300
     wasted requests. A budget says: "this whole site has failed enough,
     stop retrying anything on it."
   - *Content-hash dedup*: today dedup is by URL, so if `/home` and
     `/index` are the same page, both are fetched. Hashing each page's
     content would let the crawler recognise "seen this exact page
     before" regardless of URL.
