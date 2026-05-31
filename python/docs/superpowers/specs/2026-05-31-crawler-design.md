# Single-Domain Web Crawler — Design

**Status:** Draft for review
**Date:** 2026-05-31
**Scope:** The actual crawl logic for the `crawler` CLI (Zego exercise). The
scaffolding (Typer app, tooling, Docker) already exists; the `crawl` command is
currently a stub. This document covers the HTTP client, HTML link extraction,
async fan-out, domain filtering, the layered architecture, and the testing
strategy.

Companion doc: [`2026-05-31-python-cli-scaffolding-design.md`](./2026-05-31-python-cli-scaffolding-design.md)
(the skeleton this builds on).

---

## 1. Goal

Given a base URL, crawl **only that domain**, and for every page print the page
URL and all links found on it. Links to other domains **and subdomains** are
listed but never followed. Use concurrency to run fast without sacrificing
accuracy or wasting compute. No Scrapy/Playwright; libraries for HTTP and HTML
parsing are fine.

The exercise is judged on **software design, structure, and testing** — not just
a working result — so the architecture and its seams are first-class deliverables.

---

## 2. Web-crawler criticalities — and which apply here

A web crawler has many well-known failure modes. The table records the full set,
the decision for this exercise, and the rationale. "Don't overengineer" is an
explicit constraint, so several real concerns are deliberately scoped out and
documented rather than built.

### Build now (core correctness / competence)

| Concern | Decision |
| --- | --- |
| **URL normalization** | Strip fragments, lowercase host, drop default ports (`:80`/`:443`), resolve relative/protocol-relative links via `urljoin`. *Not* normalizing trailing slashes or query order — too risky, can merge distinct pages. |
| **Domain matching** | Follow iff `host == seed_host` (case-insensitive, port-normalized). `www.` and other subdomains are listed, not followed (the brief says subdomains count as other domains). |
| **Dedup / visited set** | A URL is recorded as visited at enqueue time; guarantees termination on cycles and avoids redundant fetches. Quality of dedup == quality of normalization. |
| **Bounded async concurrency** | `asyncio` + one shared `httpx.AsyncClient` (pooling/keep-alive) + a fixed worker pool of size N. This is both the speed lever and the politeness lever. |
| **Per-page failure isolation** | A 404/timeout/garbage page is recorded as an error on that page and never aborts the crawl. |
| **Timeouts** | Connect + read timeouts so one hanging server can't stall the run. |
| **Content-Type gating** | Only parse `text/html`; skip PDFs/images/binaries. Serves "don't waste compute." |
| **Lenient link extraction** | Tolerant HTML parser; filter non-navigable schemes (`mailto:`, `tel:`, `javascript:`, `data:`). |
| **Correct completion detection** | An in-flight counter (not "queues empty") decides when the crawl is genuinely done. The classic place crawlers hang or exit early. |
| **Testability seams (DI)** | Ports for every I/O boundary so the engine runs against in-memory fakes with zero network. This is what the exercise actually grades. |

### Build simplified (thin version; limits noted)

| Concern | Decision |
| --- | --- |
| **Redirects** | Followed; the **final** URL is re-checked against the seed host, and both URLs marked visited. |
| **Politeness** | Concurrency cap + descriptive `User-Agent`. No adaptive throttling. |
| **Safety bound** | Optional `--max-pages`; stops enqueueing past the cap and prints a truncation notice to **stderr** so truncation never masquerades as completeness. |
| **Response-size cap** | Avoid loading a multi-GB body into memory. |
| **Deterministic output** | Async finishes in arbitrary order; per-page links are sorted so output is stable and testable. |

### Out of scope (documented as future work, not built)

robots.txt enforcement (a real **no-op placeholder** seam is provided) · retries
with backoff · JS-rendered links (**excluded by the no-Playwright constraint —
stated as a limitation**) · sitemap.xml · `rel="nofollow"` · crawler-trap
heuristics (calendar/session-id infinite spaces) · persistent/distributed
frontier (Kafka/SQS/Redis) · content-hash dedup · auth/cookies · results
persistence.

---

## 3. Architecture

### 3.1 Layers (Clean Architecture; dependencies point inward)

```
src/crawler/    OUTER · CLI = composition root. Knows domains + gateways.
src/domains/    INNER · crawl engine + ports. Pure: stdlib + typing only.
src/gateways/   OUTER · adapters to the outside world. Implement domain ports.
```

`domains` imports nothing from `crawler`/`gateways`. The CLI is the composition
root: it constructs the gateway adapters and the default stages, injects them
into the engine (manual constructor DI, no framework), runs the crawl, and
formats output.

**Placement rule:** the domain imports only stdlib + typing; every third-party-
or infrastructure-backed implementation lives in `gateways`. The single
deliberate exception is the **default stages**, kept in-domain now for
testability — they depend only on ports, so extracting them to gateways later
(e.g. stages that call external fetch/parse services) is a move, not a rewrite.

### 3.2 Module layout

```
src/
  crawler/                    OUTER · CLI
    cli.py                    build ports+stages+engine, inject, run, stream
    output.py                 PageResult -> text / JSONL (stdout); logs+notices -> stderr
  domains/crawler/            INNER
    __init__.py               public surface (Crawler, models, ports)
    models.py                 FetchResult · PageResult · ParseOutcome · CrawlConfig (frozen)
    ports.py                  Fetcher · LinkExtractor · Queue ·
                              RobotsPolicy · FetchStage · ParseStage  (Protocols)
    urls.py                   normalize() · same_host() · resolve()  (pure, stdlib urllib)
    engine.py                 Crawler coordinator (async-iterator API)
    stages/
      fetch_stage.py          DefaultFetchStage(Fetcher, RobotsPolicy)  in-domain, extractable
      parse_stage.py          DefaultParseStage(LinkExtractor)          in-domain, extractable
    robots.py                 NoOpRobotsPolicy (always True; docstring: impl before prod)
  gateways/
    http/httpx_fetcher.py            HttpxFetcher         -> Fetcher
    parsing/selectolax_extractor.py  SelectolaxExtractor  -> LinkExtractor
    memory/queue.py                  InMemoryQueue        -> Queue   (wraps asyncio.Queue)
```

`gateways` holds only the HTTP fetcher, the parser, and the in-memory queue
adapter — no database/repository. The visited set is a plain in-process `set`
owned by the coordinator (output goes to stdout, so there is nothing to persist).
That is the "create gateways only if necessary" call made concrete.

### 3.3 Ports (defined in `domains/crawler/ports.py`)

```python
class Fetcher(Protocol):                                   # gateway: httpx
    async def fetch(self, url: str) -> FetchResult: ...

class LinkExtractor(Protocol):                             # gateway: selectolax (swappable)
    def extract(self, html: str, base_url: str) -> list[str]: ...

class Queue(Protocol):                                     # gateway: in-memory (Kafka/SQS later)
    async def put(self, item: object) -> None: ...
    async def get(self) -> object: ...

class RobotsPolicy(Protocol):                              # domain: NoOp placeholder
    async def allowed(self, url: str) -> bool: ...

class FetchStage(Protocol):                                # domain default; extractable to gateway
    async def fetch(self, url: str) -> FetchResult: ...

class ParseStage(Protocol):                                # domain default; extractable to gateway
    async def parse(self, result: FetchResult) -> ParseOutcome: ...
```

- **Fetcher / LinkExtractor** — the low-level I/O + parsing seams. `LinkExtractor`
  is sync and pure (selectolax has no I/O); swapping to lxml/bs4 is a one-line
  injection change because nothing in the domain imports the parser.
- **Queue** — the message-passing seam. Two instances: the **frontier** (URLs to
  fetch) and the **results** queue (fetched HTML to parse). The port is minimal
  (`put`/`get`); **termination is owned by the engine, not delegated to the
  queue**, because `asyncio.Queue.join()`/`task_done()` semantics do not exist in
  Kafka/SQS and would leak through the abstraction.
- **RobotsPolicy** — injected into the **fetch stage** (not the coordinator).
  `NoOpRobotsPolicy.allowed()` always returns `True`, with a docstring stating a
  real robots.txt-fetching policy must be implemented before production. Keeping
  the check in the fetch stage keeps the coordinator's enqueue path purely
  synchronous (see §4.2).
- **FetchStage / ParseStage** — the two stages as ports. The coordinator depends
  on these abstractions; `DefaultFetchStage` depends on `Fetcher` + `RobotsPolicy`,
  `DefaultParseStage` on `LinkExtractor`. When a stage moves to an external
  service, only the implementation changes.

The **visited set** is intentionally *not* a port — it is a plain `set[str]`
owned by the coordinator. It is single-writer (only the coordinator mutates it)
and inseparable from in-process termination, so abstracting it now would be
ceremony without payoff. Promoting it to a `VisitedStore` port + Redis adapter is
the first step of the distributed evolution path (§10).

### 3.4 Models (`models.py`, frozen dataclasses)

```python
FetchResult(requested_url, final_url, status, content_type, html: str | None, error: str | None)
PageResult(url, links: tuple[str, ...], status: int | None, error: str | None)   # links sorted
ParseOutcome(page: PageResult, on_host_links: tuple[str, ...])                    # candidates, pre-dedup
CrawlConfig(seed_url, seed_host, concurrency, timeout, max_pages, user_agent, max_bytes)
```

A robots-disallowed or non-HTML URL still produces a `FetchResult` (with
`html=None` and a reason in `error`), so it flows through the results queue and
the coordinator's in-flight accounting stays balanced — it simply yields a
`PageResult` with no links. The coordinator special-cases nothing.

A robots-disallowed or non-HTML URL still produces a `FetchResult` (with
`html=None` and a reason in `error`), so it flows through the results queue and
the coordinator's in-flight accounting stays balanced — it simply yields a
`PageResult` with no links. The coordinator special-cases nothing.

---

## 4. Concurrency, data flow, and termination

Two stages connected by two queues, with a coordinator that closes the loop.

```
                        +-----------------------------------------------+
                        |            domains/crawler (engine)           |
                        |   coordinator: visited set · in_flight ·      |
                        |   on-host classify · termination · loop-back  |
   seed --->            +------+--------------------------------^-------+
                               | put(seed)                      | put(on-host, unseen)
                +--------------v-------------+                  |
   Queue PORT   |  FRONTIER  (queue of URLs) |                  |
  (gateway) ----+--------------+-------------+                  |
   in-mem now   |              | get()                          |
   Kafka/SQS    |     +--------v---------+                      |
   later        |     | FETCH STAGE x N  |-- Fetcher port ------+--> httpx (gateway)
                |     |  robots gate      |-- RobotsPolicy ------> (NoOp now)
                |     |  url -> HTML      |                      |
                |     +--------+---------+                       |
                |              | put(FetchResult)                |
                |  +-----------v-----------+                     |
   Queue PORT   |  | RESULTS (queue: HTML) |                     |
  (gateway) ----+  +-----------+-----------+                     |
                               | get()                           |
                     +---------v---------+                       |
                     | PARSE STAGE x 1   |-- LinkExtractor port -+--> selectolax (gateway)
                     |  HTML -> links    |                       |
                     |  normalize/classify -----------------------+ (on-host candidates)
                     +---------+---------+
                               | emit PageResult
                               v
                        output stream --> CLI prints (stdout)
```

### 4.1 Why one parse loop and N fetch workers

`asyncio` is single-threaded: N workers buy concurrency on **network waits**, not
on CPU. Link extraction is CPU work that serializes on the event loop regardless,
so a single parse loop costs nothing in throughput and buys a big simplification:
**the visited set, the in-flight counter, and the frontier have exactly one
writer** — no locks, no check-then-act races.

### 4.2 Coordinator algorithm (in `engine.py`)

Kept deliberately low in cognitive complexity: each method does one thing, the
branching is shallow, and `visited`/`in_flight` are mutated only here (single
writer → no locks). The robots check lives in the fetch stage, so the
coordinator's enqueue path is purely synchronous.

```python
class Crawler:
    # _visited: set[str] and _in_flight: int are private, coordinator-owned

    async def crawl(self) -> AsyncIterator[PageResult]:
        self._enqueue(self._config.seed_url)
        workers = self._spawn_workers()
        try:
            while self._in_flight > 0:          # termination, NOT "queues empty"
                yield await self._process_one()
        finally:
            await self._stop_workers(workers)

    async def _process_one(self) -> PageResult:
        outcome = await self._parse_stage.parse(await self._results.get())
        for url in outcome.on_host_links:
            self._enqueue_if_new(url)
        self._in_flight -= 1
        return outcome.page

    def _enqueue_if_new(self, url: str) -> None:
        if url not in self._visited and not self._at_cap:
            self._enqueue(url)

    def _enqueue(self, url: str) -> None:       # the only writer of visited / in_flight
        self._visited.add(url)
        self._in_flight += 1
        self._frontier.put_nowait(url)

    @property
    def _at_cap(self) -> bool:
        cap = self._config.max_pages
        return cap is not None and len(self._visited) >= cap

    def _spawn_workers(self) -> list[Task]:
        return [create_task(self._worker()) for _ in range(self._config.concurrency)]

    async def _worker(self) -> None:            # pure: consumes frontier, produces results
        while (url := await self._frontier.get()) is not _SENTINEL:
            await self._results.put(await self._fetch_stage.fetch(url))

    async def _stop_workers(self, workers: list[Task]) -> None:
        for _ in workers:
            self._frontier.put_nowait(_SENTINEL)
        await gather(*workers)
```

The cap guard in `_enqueue_if_new` is the only real branch; everything else is
straight-line. `_worker` never touches `_visited` or `_in_flight`, which is what
makes the single-writer invariant hold without locks. When the cap is hit, the
coordinator emits a one-line "truncated at N" notice to stderr (§4.4).

### 4.3 Termination (the subtle part)

`in_flight` is incremented when a URL is enqueued and decremented after its HTML
has been parsed. "Both queues empty" is **not** sufficient — a worker can be
mid-fetch with nothing queued. When `in_flight` reaches 0 the crawl is genuinely
done: the coordinator pushes one `SENTINEL` per worker into the frontier, each
worker's `get()` returns the sentinel and the worker exits, `gather` completes,
and the async iterator ends.

**This in-process counter is a deliberate, temporary realization of a concept,
not the end state.** The ideal model is "dispatch worker tasks, then wait until
all are done" — what a task framework (e.g. Celery `task.delay()` + a result
group) gives you. The catch: a crawl frontier is **dynamic and recursive** —
every task discovers more URLs that spawn more tasks — so `group`/`chord` /
`AsyncResult` only let you await the tasks you *explicitly* fired, not the ones
those tasks spawn. Knowing the whole recursive crawl is finished therefore still
requires shared completion tracking: a counter in the result backend (e.g. Redis)
that tasks increment on dispatch and decrement on completion, with "am I the
last?" logic. So the in-flight counter does not disappear under a task framework —
**it moves from a process-local `int` into the backend** (see §10.4).

We deliberately **do not** introduce a "task dispatcher / await-all" port now.
That would be overengineering: the `FetchStage` and `Queue` ports are already the
seams that map onto a Celery worker + broker, and a single dispatch/await
abstraction cannot honestly span the in-process **centralized** model (one
coordinator owns completion) and the distributed **decentralized** model (tasks
recursively spawn tasks; completion lives in the backend) — it would be the
asyncio version wearing a costume, with one real implementation.

### 4.4 max-pages

The coordinator stops enqueueing once the visited count reaches `--max-pages`,
and emits a "truncated at N" notice to **stderr**.

---

## 5. Library choices

- **httpx** (async, HTTP/2, connection pooling, `follow_redirects=True`) over
  aiohttp — cleaner API; the final URL after redirects is re-checked against the
  seed host.
- **selectolax** as the default parser — markedly faster than lxml/BeautifulSoup
  (matters per the brief), lenient on malformed HTML. Low-risk because it sits
  behind `LinkExtractor`; lxml/bs4 is a one-line swap.
- **pytest-httpx** for hermetic fetcher tests (mocked transport, no network).

Link extraction pulls `<a href>`, `<area href>`, and `<link href>` (navigation-
oriented). Non-HTTP schemes and fragments are filtered in `urls.normalize()`.

---

## 6. Output

- Default: human-readable text to **stdout** — each page URL, then its sorted
  links indented beneath.
- `--json`: one JSON object per line (JSONL), pipe-friendly.
- Logs, progress, and truncation notices go to **stderr** so stdout stays clean
  for piping.

---

## 7. CLI surface

```
crawler crawl URL [--concurrency N] [--timeout S] [--max-pages N] [--json]
```

`@runnify` stays the innermost decorator under `@app.command()` (see scaffolding
doc) so `typer.Exit` and exit codes behave.

---

## 8. Testing strategy

| Target | Approach |
| --- | --- |
| `urls.py` | Pure unit tests: fragments, default ports, protocol-relative, `..`, host case, scheme filtering. |
| `SelectolaxExtractor` | HTML fixtures: anchors/area/link, relative + `<base href>`, malformed markup. |
| `DefaultFetchStage` / `DefaultParseStage` | Unit tests with fake ports; fetch-stage test covers the robots gate (NoOp allows; a disallowing fake yields a skipped `FetchResult`). |
| `engine.py` | Near-end-to-end with a **FakeFetcher** over an in-memory site graph + real default stages + real extractor + in-memory queue + plain visited set (zero network): every page emitted once, cross-host links listed-not-followed, cycles terminate, errors recorded, `max_pages` honored. |
| `HttpxFetcher` | Hermetic via **pytest-httpx**: redirects, non-HTML content-type, timeouts, 4xx/5xx. |
| `cli.py` | Typer `CliRunner` with fakes injected through a build seam: exit codes, text + `--json` output. |

`asyncio_mode = "auto"` (already configured) means `async def test_*` run without
per-test markers.

---

## 9. New dependencies

- Runtime: `httpx`, `selectolax`.
- Dev: `pytest-httpx`.

(Existing: typer, asyncer, pytest, pytest-asyncio, ruff, ty.)

---

## 10. Evolution path (how this scales, without building it now)

The seams are placed so the single-process crawler becomes a distributed one by
swapping adapters, not rewriting the engine:

1. **Queues → external broker.** Replace `InMemoryQueue` with a Kafka/SQS/RabbitMQ
   adapter implementing the same `Queue` port.
2. **Visited set → shared store.** Promote the plain `set` to a new `VisitedStore`
   port + Redis adapter (`add_if_new` → `SADD`, which returns whether the member
   was new). Required the moment multiple parser workers run, or they re-crawl
   each other's URLs.
3. **Stages → separate workers.** `FetchStage` and `ParseStage` become
   gateway-backed implementations / separate deployable workers consuming and
   producing to the external queues.
4. **Coordinator → task framework + frontier service.** Each `FetchStage` /
   `ParseStage` becomes a worker task (`fetch_task.delay(url)` etc.); the broker
   is the queue. The process-local **in-flight counter relocates to the result
   backend** as a shared counter (incremented on dispatch, decremented on
   completion). Because the frontier is dynamic/recursive, you cannot simply
   "await the group" — only explicitly-fired tasks are in a `group`/`chord`/
   `ResultSet`, not the ones they spawn — so **distributed termination is a
   genuine problem** requiring that shared counter plus "am I the last?"
   coordination. Called out as future work, not solved here. The same applies to
   the visited set (step 2): both pieces of coordinator state become shared
   backend state.

The CLI is acknowledged (per the brief) as the wrong long-term interface for
multi-domain / large-scale crawling; a queue-driven service with the same domain
core is the intended direction, which this layering already supports.

---

## 11. Documentation deliverable

Documentation is a graded deliverable, not an afterthought: the brief explicitly
asks the `python/README.md` to carry a written discussion of design decisions and
trade-offs. The implementation plan therefore includes an explicit **documentation
step** (run after the code lands, so the prose matches what was actually built),
producing:

1. **Architecture documentation** — extend `python/README.md` with an
   "Architecture & design" section covering:
   - the layering (Clean Architecture: `crawler` / `domains` / `gateways`) and the
     dependency-inward rule;
   - the two-stage fetch/parse pipeline, the two queues, and the coordinator;
   - the ports (Fetcher, LinkExtractor, Queue, RobotsPolicy, FetchStage,
     ParseStage) and what each seam enables;
   - termination via the in-flight counter (and why "queues empty" is insufficient).

2. **Diagrams in MermaidJS** — the ASCII diagrams in this spec are re-expressed as
   Mermaid so they render on GitHub. At minimum:
   - a **component/layer diagram** (`flowchart`) showing CLI → domain engine →
     gateways and the dependency direction;
   - a **data-flow diagram** (`flowchart`) of seed → frontier → fetch workers ×N →
     results queue → parse loop → loop-back / output;
   - optionally a **sequence diagram** of one page's lifecycle (fetch → robots gate
     → parse → classify → enqueue/emit).
   Each diagram gets a one-line caption; diagrams supplement prose, never replace it.

3. **Reasoning behind the choices** — concise rationale for the decisions in this
   spec: asyncio over threads (I/O-bound); single parse loop / single-writer state
   (no locks); httpx + selectolax (and why each sits behind a port); ports-and-DI
   for testability; the deliberate non-abstractions (visited set as a plain `set`).

4. **Trade-offs and possible improvements** — the deliberate, time-boxed cuts and
   the discussed future work, drawn from §2 (non-goals), §10 (evolution path to a
   distributed crawler), and the conversation:
   - robots.txt enforcement (currently a NoOp placeholder seam);
   - distributed mode: external queue broker, shared `VisitedStore` (Redis), split
     worker processes, and the distributed-termination problem;
   - why a CLI is the wrong long-term interface and what replaces it;
   - JS-rendered pages being out of scope (no-Playwright constraint).

5. **AI-tooling disclosure** — the brief asks which IDE and AI tools were used and
   how. Add a short "Tooling & AI usage" note (this design was developed
   interactively with Claude Code: brainstorming → spec → plan → implementation).

The README discussion and the diagrams should stay consistent with this spec and
the scaffolding spec; where they would diverge, the **code is the source of truth**
(per `CLAUDE.md`) and the docs are updated to match.

---

## 12. Non-goals (restated)

robots.txt enforcement (placeholder only) · retries/backoff · JS-rendered links
(no-Playwright limitation) · sitemap.xml · `nofollow` · crawler-trap heuristics ·
persistent/distributed frontier · content-hash dedup · auth/cookies · results
persistence. These belong in the README's design-discussion section as
deliberate, time-boxed trade-offs.
