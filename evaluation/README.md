# Web Crawler Test Harness

## Motivation

When evaluating code challenge submissions for the web crawler exercise, manual testing is time-consuming and inconsistent. Different reviewers may test different scenarios, making it difficult to compare candidates fairly.

This test harness provides automated, repeatable validation of crawler submissions against the exercise requirements:

1. Accept a base URL and crawl the site
2. Print the URL of each page and all URLs found on it
3. Only crawl URLs within the seed domain (not subdomains or external domains)

The harness is language-agnostic - it works with any executable that accepts a URL argument and prints output to stdout.

## How It Works

1. **Starts a local test server** with a controlled set of HTML pages containing known links
2. **Executes the candidate's crawler** pointing at the test server
3. **Tracks which pages were fetched** via server access logs
4. **Extracts URLs from output** using flexible regex parsing (works with JSON, plain text, tables, etc.)
5. **Validates requirements** by comparing fetched pages vs printed URLs

### Test Site Structure

```
/                 -> /about, /contact, /products, external-domain.com, sub.{host}
/about            -> /, /team
/contact          -> /, mailto:, tel:, javascript:
/products         -> /products/item1, /products/item2
/products/item1   -> /products, /about
/products/item2   -> /products, external-domain.com
/team             -> /about, linkedin.com, twitter.com
/isolated         -> (NOT linked from anywhere - should not be crawled)
```

### Tests Performed

| Test | Description |
|------|-------------|
| Crawler executes | Runs without crashing |
| Crawls seed page | Fetches the root URL |
| Crawls all same-domain pages | Discovers and fetches all 7 linked pages |
| Does not crawl unlinked pages | Skips `/isolated` (no inbound links) |
| Does not crawl external domains | No requests to `external-domain.com` |
| Does not crawl subdomains | No requests to `sub.*` |
| Prints external URLs | External links appear in output (printed, not crawled) |
| Prints subdomain URLs | Subdomain links appear in output |
| Handles non-HTTP schemes | Doesn't crash on `mailto:`, `tel:`, `javascript:` |
| No duplicate page fetches | Each page fetched exactly once |
| Produces output | URLs found in stdout/stderr |

## Requirements

- Python 3.8+
- No external dependencies (uses only standard library)

## Usage

```bash
python3 crawler_test_harness.py [OPTIONS] <command> [args...]
```

The test harness appends the seed URL to the provided command and captures output.

### Options

| Option | Description |
|--------|-------------|
| `--timeout`, `-t` | Timeout in seconds (default: 60) |
| `--verbose`, `-v` | Show crawler output |

### Examples

```bash
# Python submission
python3 crawler_test_harness.py python crawler.py

# Shell script wrapper
python3 crawler_test_harness.py ./run_crawler.sh

# Java JAR
python3 crawler_test_harness.py java -jar crawler.jar

# With longer timeout for slow builds
python3 crawler_test_harness.py --timeout 120 ./run_crawler.sh

# With verbose output to debug failures
python3 crawler_test_harness.py --verbose python crawler.py
```

### Creating Wrapper Scripts

For submissions that require specific setup (e.g., sbt, virtual environments), create a wrapper script:

**Scala/sbt example** (`run_crawler.sh`):

```bash
#!/bin/bash
cd "$(dirname "$0")"
sbt --error "run $1" 2>&1
```

**Python with venv example** (`run_crawler.sh`):

```bash
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python crawler.py "$1"
```

**Pre-built JAR example** (`run_crawler.sh`):

```bash
#!/bin/bash
cd "$(dirname "$0")"
java -jar ./target/crawler.jar "$1" 2>&1
```

**Make the wrapper executable**:

```bash
chmod +x run_crawler.sh
```

## Output Format

The harness uses flexible URL extraction - it finds all `http://` and `https://` URLs in the output regardless of format. Candidates can output in any format:

```
# Plain text
Page: http://example.com
  link: http://example.com/about

# JSON
{"page": "http://example.com", "links": ["http://example.com/about"]}

# Tree format
URL: http://example.com
      |--  http://example.com/about
```

## Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed

## Example Output

```
Starting test server...
Test server running at http://127.0.0.1:57296
Running crawler: ./run_crawler.sh http://127.0.0.1:57296
------------------------------------------------------------
============================================================
TEST RESULTS
============================================================
PASS  Crawler executes
       OK
PASS  Crawls seed page
       Root page was fetched
PASS  Crawls all same-domain pages
       Crawled 7/7 expected pages
PASS  Does not crawl unlinked pages
       Correctly skipped /isolated
PASS  Does not crawl external domains
       No external domains crawled
PASS  Does not crawl subdomains
       Subdomain links should be printed but not crawled
PASS  Prints external URLs
       External URLs appear in output
PASS  Prints subdomain URLs
       Subdomain URLs appear in output
PASS  Handles non-HTTP schemes
       Contact page (with mailto/tel/js links) was crawled
PASS  No duplicate page fetches
       No duplicates detected
PASS  Produces output
       Found 13 URLs in output
============================================================
Results: 11/11 tests passed
ALL TESTS PASSED
```

## Troubleshooting

### Crawler times out
Increase timeout: `--timeout 180`

### Tests fail unexpectedly
Use `--verbose` to see crawler output and debug

### "Command not found" error
Ensure the executable path is correct and has execute permissions

### Duplicate fetches detected
The candidate's deduplication logic has a bug - the same URL is being fetched multiple times

### Missing pages
The crawler isn't discovering all links - check link extraction logic
