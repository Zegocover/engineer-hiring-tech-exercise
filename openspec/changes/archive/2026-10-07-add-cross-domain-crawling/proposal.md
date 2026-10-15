# Proposal

## Why

A crawl is locked to the exact host of its base URL. That is what the exercise asks for by default, but real sites are often spread across several hosts: `www.` and the apex, `blog.` or `docs.` subdomains, or a partner documentation site. Today none of those pages can be included in a crawl. The brief also asks how the design would extend beyond one domain. Letting a crawl follow links into an explicit list of extra hosts answers that, while keeping the single-host behaviour as the default.

## What Changes

- **Crawl scope can include extra hosts.** A crawl takes an optional list of host patterns that are followed in addition to the base URL's host:
  - an exact host, such as `docs.partner.io` or `localhost:8001`;
  - a subdomain wildcard, such as `*.example.com`, which matches any subdomain of `example.com` but not `example.com` itself.

  Links to hosts outside the scope are still reported but not fetched. With no patterns, the crawl behaves exactly as today.
- **Redirects:** a redirect is followed when its final URL is in scope, on any allowed host. Redirects leaving the scope are still dropped.
- **robots.txt per host:** it is read separately for each host the crawl reaches, the first time that host is reached, and applied to that host's URLs.
- **Per-host concurrency cap:** a new optional limit on how many requests run against any one host at once, within the overall concurrency. By default there is no extra cap, so single-host crawls are unchanged.
- **Every surface supports it:**
  - **Library:** new `CrawlConfig` fields, `allowed_hosts` and `per_host_concurrency`, which are validated.
  - **CLI:** `--allow-host PATTERN` (repeatable) and `--per-host-concurrency N`. The default stays single-host, as the brief requires.
  - **API:** `POST /crawls` accepts `allowed_hosts` and `per_host_concurrency`, which are reported in the crawl's limits. The number of patterns is bounded.
  - **Dashboard:** the start form gets an "Also follow hosts" field and a per-host concurrency field, and the crawl view shows the allowed hosts. The generated API types are regenerated.
- **Not included:** multiple seed URLs in one crawl, per-host statistics, `Crawl-delay` and rate limiting, and wildcards other than a leading `*.`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-crawl`:
  - "Only the exact crawl host is followed" becomes "Only in-scope hosts are followed": the base host plus allowed patterns.
  - "Redirects leaving the host are not followed" becomes "Redirects leaving the crawl scope are not followed".
  - robots.txt applies per host.
  - Crawl limits gain the per-host concurrency cap.
- `crawl-api`:
  - Starting a crawl accepts the new options.
  - A crawl's details report them.
  - The crawl rules refer to the scope rather than a single host.
  - New: the size of the allowed-hosts list is bounded.
- `crawl-dashboard`:
  - The start form gains the new fields.
  - The crawl view shows the allowed hosts.

`crawler-extension-api` is unchanged. Custom parsers still can't widen the scope themselves, because the scope comes only from the crawl's configuration.

## Impact

- **Library (`python/src/site_crawler`):**
  - `models/config.py`: new fields and their validation.
  - `core/urls.py`: host pattern matching.
  - `core/crawler.py`: scope checks, per-host robots.txt, per-host concurrency.
  - `core/robots.py`: loading per host.
  - `cli.py`: new options.
  - Tests and README.
- **Backend (`python/backend`):**
  - `schemas.py` and `service.py`: new request fields and limits.
  - Tests and README.
- **Dashboard (`front-end`):**
  - Regenerated `src/lib/api`.
  - `StartCrawlForm` and `CrawlView`.
  - Tests and README.
- **Compatibility:** everything new is optional and defaults to today's behaviour. API clients that don't send the new fields see only two new fields in a crawl's `limits`.
