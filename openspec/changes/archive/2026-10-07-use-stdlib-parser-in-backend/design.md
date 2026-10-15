# Design

## Context

See proposal.md for motivation. Paths are relative to `engineer-hiring-tech-exercise/python/backend/`.

**The `Parser` protocol (from `site_crawler.interfaces`):** `parse(page: FetchResult) -> list[str]` returns link strings found in the page.
- The strings may be relative; the crawler resolves and normalises them against `page.final_url` and de-duplicates them.
- A parser that honours `<base href>` must return links already joined with it.
- The crawler calls `parse` synchronously, on the event loop.

**What `DefaultSelectolaxParser` does today** (the behaviour to match):
1. It parses `page.body` (bytes) with Lexbor, which detects the encoding itself.
2. It applies the first `<base href>` element anywhere in the document (`css_first("base[href]")`), joined with `page.final_url`, to every link, including links that come before the `<base>` element.
3. It returns `<a href>` values in document order, with whitespace trimmed, skipping empty or blank ones. Other elements (`<link>`, `<img>`, `<script src>`) are ignored. Duplicates are kept, because the crawler removes them.
4. Malformed markup is tolerated: unquoted or mixed-case attributes, unclosed elements, anchors in stray table content.
5. Non-UTF-8 bytes don't crash it.

**The library's parser tests** (`python/tests/test_parsers.py`) cover points 2 to 5 with six cases. They're a ready-made acceptance set.

**Measured cost** on the same machine, for a synthetic 207 KiB page with 1,500 anchors (an average of 20 runs):

| Parser | Time per page | Links |
|---|---|---|
| selectolax | 3.0 ms | 1,500 |
| `html.parser` | 27.9 ms | 1,500 |

## Goals / Non-Goals

**Goals:**
- A backend-owned parser on `html.parser` that produces the same links as `DefaultSelectolaxParser` for the same input.
- Parity that's demonstrated by tests, not assumed.

**Non-Goals:**
- Changing the library, the CLI or any default.
- Making the parser selectable (rejected in favour of always using it in the backend).
- Moving parsing off the event loop.
- Extracting more than `<a href>` (such as `<area>`, `<link rel=next>` or canonical links).

## Decisions

### 1. Collect while streaming, join the base once at the end

`html.parser.HTMLParser` is event-driven and sees the document front to back. A small subclass records three things as it goes:
- the `href` of the **first** `<base>` start tag that has one (later ones are ignored, as with `css_first`);
- the `href` of every `<a>` start tag, including self-closing ones handled through `handle_startendtag`, stripped and skipped when empty;
- nothing else. Anything inside `<template>` is ignored, including nested templates. HTML5 treats template content as inert, and the comparison test showed selectolax skips it.

After `close()`, if a base was found it's joined with `page.final_url` and applied to every collected `href` with `urljoin`. Otherwise the raw `href`s are returned. Joining at the end, rather than as each link is seen, reproduces selectolax's behaviour for links that appear before `<base>`.

`html.parser` already does what the rest needs:
- lowercases tag and attribute names, so `HREF` works;
- accepts unquoted attribute values;
- unescapes character references in attribute values (`convert_charrefs=True`);
- treats `<script>` and `<style>` content as raw text, so anchors written inside scripts are not links, as in Lexbor.

The parser instance is created per call, so the adapter stays stateless and safe to share between crawls.

Alternatives considered:
- *Join each link with the base as it's seen.* That gives different results whenever `<base>` comes after an anchor.
- *A regular expression over the HTML.* It breaks on comments, scripts and attribute quoting, which is the reason to use a parser at all.

### 2. Decoding bytes

`html.parser` takes text, so the body is decoded before parsing:
1. Use the `charset=` parameter of `page.content_type` when Python knows that codec.
2. Otherwise decode as UTF-8.
3. Either way, use `errors="replace"`, so undecodable bytes become U+FFFD and a crawl never crashes.

`<meta charset>` sniffing isn't done.

*Found during implementation:* selectolax, as the library calls it, doesn't sniff it either. A page whose charset is declared only in a `<meta>` tag gives the same result from both parsers. selectolax also ignores the charset in the Content-Type header, which this parser honours. The one difference the comparison found is therefore in this parser's favour: a Latin-1 page served with `charset=ISO-8859-1` gives `/café` here, and `/caf�` from selectolax. The test records it as an explicit, expected difference.

### 3. Where it lives and how it's wired

- **`adapters.py`** gains `StdlibHtmlParser` next to `SharedClientFetcher` and `JobWriter`. That module's docstring already says the backend gives every crawl its components explicitly.
- **`service.py`** passes `parser=StdlibHtmlParser()` instead of `DefaultSelectolaxParser()`, and the selectolax import goes.
- It's typed against `site_crawler.interfaces.Parser` in a test (`parser: Parser = StdlibHtmlParser()`), so mypy checks that it matches the protocol.

### 4. Proving parity

- **Port the library's six parser cases** to `tests/test_parser.py` against the new parser, with the same expected values.
- **Add a differential test.** A table of tricky snippets goes through both `StdlibHtmlParser` and `DefaultSelectolaxParser`, and the output must be identical. selectolax is installed in the backend's environment as a library dependency. The snippets cover:
  - a base after the anchors;
  - two bases (the first wins);
  - an absolute base and an empty base;
  - entities in an `href` (`&amp;`);
  - an anchor inside a comment, and inside `<script>` and `<template>`;
  - self-closing `<a/>`;
  - uppercase tags;
  - whitespace-only and missing `href`;
  - nested and unclosed tags;
  - SVG `<a xlink:href>`;
  - a non-UTF-8 body with a charset in the Content-Type header.
- **Handle known differences honestly.** If a snippet differs in a way that doesn't matter (for example, how HTML5 treats `<template>` content), the test documents it as an explicit expected difference with a comment. It isn't silently dropped from the table.
- **End to end:** the existing API tests and the Docker smoke test run through the real service, so they exercise the new parser with no changes.

## Risks / Trade-offs

- [About 9 times slower parsing (28 ms for a 207 KiB page), on the event loop] → For typical pages (20-100 KiB) that's roughly 3-14 ms per page. Fetch latency dominates crawl time, so this is acceptable for a demo service. The README states the trade-off. Moving parsing to a thread would need the library's crawler to call parsers off the loop, which is future work there.
- [Parity gaps on unusual markup] → The differential test makes every known gap explicit. The API tests and the Docker smoke test check real pages end to end.
- [Pages that declare a charset only in a `<meta>` tag] → Both parsers decode them as UTF-8, so results are identical (checked by the comparison test). URLs are almost always ASCII or percent-encoded anyway.
