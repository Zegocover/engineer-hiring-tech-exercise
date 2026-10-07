# Design

## Context

See proposal.md for motivation and the three spec deltas for behaviour. Paths are relative to `engineer-hiring-tech-exercise/python/` unless stated otherwise.

How the crawler works today (`src/site_crawler/core/crawler.py`):

- **Scope is one host.** `self._host = host_key(base_url)`, and `same_host(url, self._host)` gates both `_enqueue` and `_accept_final_url` (redirects). `host_key` is the hostname plus any non-default port, with the scheme ignored.
- **`_enqueue` is synchronous on purpose:** the check-and-insert into `_seen` with no `await` is what guarantees each URL is fetched at most once.
- **robots.txt is loaded once, before the seed is queued.** `RobotsGate.load(fetcher, seed, ua)` runs, and `_enqueue` then calls `self._robots.allowed(url)` synchronously. A URL that robots.txt disallows is marked seen and counted in `robots_skipped` before `_enqueued` is incremented, so it doesn't use up the page budget.
- **The queue holds `(url, depth)`.** N workers each fetch, parse and enqueue, and `queue.join()` signals that the crawl is done.
- **`CrawlConfig`** is a frozen, validated dataclass. The CLI, the backend's `CrawlService.start` and the dashboard all build on it.

## Goals / Non-Goals

**Goals:**
- An explicit, validated scope: the base host plus `allowed_hosts` patterns, shared by every surface.
- robots.txt fetched per host, once, before that host's URLs are admitted, without breaking the synchronous at-most-once enqueue or the page-budget rule.
- An optional per-host concurrency cap.
- Exactly today's behaviour when neither option is used. Existing tests are untouched.

**Non-Goals:**
- Multiple seeds, per-host statistics, `Crawl-delay` or rate limiting, and a scheduler that avoids a worker blocking on a host at its concurrency cap (see Risks).

## Decisions

### 1. Host patterns and `HostScope`

The allowed patterns, validated by `parse_host_pattern(text) -> HostPattern` in `models/hosts.py`. It lives in `models` because `CrawlConfig` validates patterns and the package's layering lets `models` import only `models`. For the same reason, `ConfigError` moves to `models/errors.py`, re-exported unchanged. `HostScope` stays in `core/urls.py`.

| Form | Example | Matches |
|---|---|---|
| Exact host | `docs.partner.io`, `localhost:8001`, `[::1]:8080` | `host_key(url) == pattern` |
| Subdomain wildcard | `*.example.com` | hostnames ending in `.example.com`, on default ports only. Not `example.com` itself, which can be listed separately. |

- Patterns are lowercased, and a trailing dot is stripped.
- Each label must match `[a-z0-9-]{1,63}`, with no leading or trailing hyphen. IPv4 literals are allowed, and IPv6 literals in brackets.
- An optional `:port` is allowed on exact hosts.
- Anything else is rejected with `ConfigError` naming the pattern:
  - a scheme, path, `@` or whitespace;
  - an empty string;
  - a `*` anywhere except a leading `*.`;
  - a bare `*`.

  A bare `*` would make every host in scope, which defeats the purpose.

`HostScope(base_host, patterns)` has a single method, `allows(url) -> bool`. `Crawler` builds it once and uses it wherever it now calls `same_host`: in `_enqueue` and in `_accept_final_url`. Matching uses the existing `host_key`, so the existing rules carry over: case is ignored, default ports are ignored, and http and https on the same host count as one host.

Alternatives considered:
- *Accept full regular expressions.* They're error-prone for users and easy to write too broadly.
- *Registrable-domain matching via the Public Suffix List.* It adds a dependency, and explicit `*.` patterns cover the same need.

### 2. robots.txt per host, as a queue item

The queue holds two kinds of item:

```python
Fetch(url, depth)        # as today
LoadRobots(host, origin) # fetch https://host/robots.txt once, then admit that host's waiting URLs
```

```
_enqueue(url, depth)          (synchronous, as today)
  seen? out of scope? too deep?  -> drop
  mark seen
  if robots disabled or gate[host] loaded:  _admit(url, depth)
  else:
      pending[host].append((url, depth))
      if host not requested yet: queue LoadRobots(host, origin-of-url)

worker: LoadRobots(host)
  gate[host] = await RobotsGate.load(fetcher, origin, ua)   (inside the host's concurrency slot)
  for url, depth in pending.pop(host): _admit(url, depth)

_admit(url, depth)            (synchronous)
  robots disallows (and url != seed)? -> robots_skipped += 1; return   (no budget used)
  page budget reached?               -> return
  _enqueued += 1; queue Fetch(url, depth)
```

- **At-most-once is kept.** URLs are still marked seen synchronously in `_enqueue`. Waiting in `pending` is not a second chance to be enqueued.
- **The page budget means what it did before.** It's counted only in `_admit`, after the robots.txt check, so disallowed URLs still never use it.
- **Termination still works.** A `LoadRobots` item is ordinary queue work, so `queue.join()` can't finish while a host's robots.txt is loading and URLs are waiting on it.
- **The seed host goes through the same path.** The first queue item is `LoadRobots(seed_host)`, followed by the seed, exactly as today, where robots.txt was loaded before the seed. The seed is still exempt from robots.txt.
- `RobotsGate.load` takes the origin (`scheme://host_key/`) instead of the seed. Its behaviour (a missing or unreachable robots.txt allows everything) is unchanged.

Alternatives considered:
- *Check robots.txt in the worker just before fetching.* Disallowed URLs would then already be counted in `_enqueued` and would use up the page budget, which changes the spec'd behaviour. Undoing that count afterwards can't bring back URLs already refused for budget.
- *Load robots.txt for every allowed host up front.* Wildcard patterns name no concrete host, and it would fetch robots.txt for hosts the crawl never reaches.

### 3. Per-host concurrency: a semaphore per host

`CrawlConfig.per_host_concurrency: int | None = None`. When it's set, `Crawler` lazily creates an `asyncio.Semaphore(per_host_concurrency)` for each host. Workers acquire it around the actual fetch, for both `Fetch` and `LoadRobots`, so robots.txt requests count too. When it's `None`, no semaphore is used, so single-host crawls run exactly as today.

The trade-off is that a worker waiting on a host already at its cap doesn't pick up other hosts' work in the meantime (head-of-line blocking). Total throughput is bounded, but never incorrect. The documented guidance is to set `concurrency` to about `per_host_concurrency` multiplied by the number of busy hosts. A per-host queue with a round-robin scheduler would avoid the blocking, but it means rewriting the frontier, which is out of scope. It's listed as future work.

### 4. Configuration and surfaces

**Library:** `CrawlConfig` gains two fields:
- `allowed_hosts: tuple[str, ...] = ()`, validated and normalised in `__post_init__` (stored normalised via `object.__setattr__`, since the dataclass is frozen);
- `per_host_concurrency: int | None = None`, which must be at least 1.

| Surface | How the options are exposed |
|---|---|
| **CLI** | `--allow-host PATTERN` (`action="append"`, repeatable) and `--per-host-concurrency N` (positive integer). An invalid pattern exits with code 2 and a message, like any other `ConfigError`. |
| **Backend request** | `CrawlRequest.allowed_hosts: list[str] = []` (`max_length=50`) and `per_host_concurrency: int \| None` (`ge=1`). |
| **Backend service** | Rejects a `per_host_concurrency` above `max_concurrency` with `LimitError` (422). Invalid patterns reach `CrawlConfig` and come back as the existing `ConfigError` 422 with `loc: ["body"]`. |
| **Backend response** | `Limits` gains `allowed_hosts: list[str]` (normalised) and `per_host_concurrency: int \| None`. |
| **Dashboard API types** | Regenerated with `npm run gen:api` and committed. CI's drift check enforces that. |
| **Dashboard form** | An "Also follow hosts" textarea, split on commas and whitespace, with blanks dropped and the list sent only when it isn't empty, plus a "Per-host concurrency" number field. A 422 at `loc ["body","allowed_hosts", ...]` is mapped to the textarea by `loc[1]`, as other fields already are. |
| **Dashboard crawl view** | The limits section shows the allowed hosts (or "base host only") and the per-host concurrency (or "none"). |

### 5. Testing

| Area | What's tested |
|---|---|
| `core/urls.py` | Pattern parsing (valid and invalid cases from the table) and `HostScope.allows` (exact, wildcard, port, case, apex not matched by a wildcard). |
| Crawler, with `FakeSite` serving several hosts and per-host `robots.txt` | Allowed exact host followed; wildcard; out-of-scope link only reported; redirect to an allowed host; robots.txt fetched once per host and applied per host; disallowed URLs on an allowed host don't use the budget; the per-host cap is never exceeded (a fetcher that records in-flight requests per host); no options behaves as before (the existing suite). |
| CLI | Both options reach `CrawlConfig`; an invalid pattern exits 2. |
| Backend | The start scenarios, details (empty and non-empty `allowed_hosts`), an allowed host's pages in the results, an invalid pattern, 51 patterns, and `per_host_concurrency` above the maximum. |
| Dashboard | The also-follow-hosts form scenario, the field-level 422 for `allowed_hosts`, and allowed hosts shown or "base host only". |

## Risks / Trade-offs

- [Head-of-line blocking under a per-host cap] → Documented, with sizing guidance and a future-work note. The cap is opt-in, so it doesn't affect default crawls.
- [Wildcards widen the crawl a lot (for example `*.wikipedia.org`)] → The page budget and depth limits still apply. The API keeps its default and maximum page budget.
- [More hosts means more robots.txt requests, and slower starts on new hosts] → One request per host, cached for the whole crawl. URLs for that host wait only while its robots.txt loads.
- [Changing the queue item type touches the core loop] → It's covered by the existing crawler tests (unchanged), plus new multi-host tests. The `LoadRobots` path is also used for the single-host case, so every existing crawl test exercises it.
- [The API response gains fields] → Purely additive. The dashboard's types are regenerated in the same change, so CI's drift check passes.
