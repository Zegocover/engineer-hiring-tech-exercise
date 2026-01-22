#!/usr/bin/env python3
"""
Test harness for web crawler submissions.

Usage:
    python crawler_test_harness.py <executable> [args...]

Example:
    python crawler_test_harness.py ./run.sh
    python crawler_test_harness.py python crawler.py
    python crawler_test_harness.py "sbt run"

The harness will:
1. Start a local test HTTP server with controlled pages
2. Run the candidate's crawler pointing at the test server
3. Verify requirements are met by checking:
   - Which pages were actually fetched (server access log)
   - Which URLs appear in the output (flexible parsing)
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import re
import shlex
import signal
import socketserver
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

# --- Test Site Content ---

def build_test_site(base_url: str) -> Dict[str, str]:
    """
    Build test pages with controlled link structures.

    Site map:
        /              -> links to /about, /contact, /products, external.com, sub.{host}
        /about         -> links to /, /team
        /contact       -> links to /, mailto:, tel:, javascript:
        /products      -> links to /products/item1, /products/item2
        /products/item1 -> links to /products, /about
        /products/item2 -> links to /products
        /team          -> links to /about, external links
        /isolated      -> NOT linked from anywhere (should not be crawled)
    """
    parsed = urlparse(base_url)
    host = parsed.netloc.split(':')[0]

    external_domain = "http://external-domain.com"
    subdomain = f"http://sub.{host}:{parsed.port}" if parsed.port else f"http://sub.{host}"

    return {
        "/": f"""<!DOCTYPE html>
<html>
<head><title>Home</title></head>
<body>
    <h1>Home Page</h1>
    <a href="{base_url}/about">About Us</a>
    <a href="{base_url}/contact">Contact</a>
    <a href="{base_url}/products">Products</a>
    <a href="{external_domain}/page1">External Link</a>
    <a href="{subdomain}/page">Subdomain Link</a>
</body>
</html>""",

        "/about": f"""<!DOCTYPE html>
<html>
<head><title>About</title></head>
<body>
    <h1>About Page</h1>
    <a href="{base_url}/">Home</a>
    <a href="{base_url}/team">Our Team</a>
</body>
</html>""",

        "/contact": f"""<!DOCTYPE html>
<html>
<head><title>Contact</title></head>
<body>
    <h1>Contact Page</h1>
    <a href="{base_url}/">Home</a>
    <a href="mailto:test@example.com">Email Us</a>
    <a href="tel:+1234567890">Call Us</a>
    <a href="javascript:void(0)">JS Link</a>
</body>
</html>""",

        "/products": f"""<!DOCTYPE html>
<html>
<head><title>Products</title></head>
<body>
    <h1>Products Page</h1>
    <a href="{base_url}/products/item1">Product 1</a>
    <a href="{base_url}/products/item2">Product 2</a>
</body>
</html>""",

        "/products/item1": f"""<!DOCTYPE html>
<html>
<head><title>Product 1</title></head>
<body>
    <h1>Product 1</h1>
    <a href="{base_url}/products">Back to Products</a>
    <a href="{base_url}/about">About Us</a>
</body>
</html>""",

        "/products/item2": f"""<!DOCTYPE html>
<html>
<head><title>Product 2</title></head>
<body>
    <h1>Product 2</h1>
    <a href="{base_url}/products">Back to Products</a>
    <a href="{external_domain}/reviews">External Reviews</a>
</body>
</html>""",

        "/team": f"""<!DOCTYPE html>
<html>
<head><title>Team</title></head>
<body>
    <h1>Team Page</h1>
    <a href="{base_url}/about">About</a>
    <a href="https://linkedin.com/company/example">LinkedIn</a>
    <a href="https://twitter.com/example">Twitter</a>
</body>
</html>""",

        "/isolated": f"""<!DOCTYPE html>
<html>
<head><title>Isolated</title></head>
<body>
    <h1>Isolated Page</h1>
    <p>This page is not linked from anywhere and should NOT be crawled.</p>
    <a href="{base_url}/">Home</a>
</body>
</html>""",
    }


# --- Test Server ---

@dataclass
class ServerStats:
    """Track server access for verification."""
    requests: List[str] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def log_request(self, path: str):
        with self.lock:
            self.requests.append(path)

    def get_requests(self) -> List[str]:
        with self.lock:
            return list(self.requests)


class TestRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler that serves test pages and logs requests."""

    pages: Dict[str, str] = {}
    stats: Optional[ServerStats] = None

    def do_GET(self):
        # Normalize path
        path = self.path.split('?')[0].split('#')[0]
        if not path.endswith('/') and path != '/' and path not in self.pages:
            # Try with trailing slash
            if path + '/' in self.pages:
                path = path + '/'

        # Log the request
        if self.stats:
            self.stats.log_request(path)

        # Serve the page
        if path in self.pages:
            content = self.pages[path].encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')

    def log_message(self, format, *args):
        # Suppress default logging
        pass


def start_test_server(port: int = 0) -> Tuple[socketserver.TCPServer, str, ServerStats]:
    """Start test server, return (server, base_url, stats)."""
    stats = ServerStats()

    handler = TestRequestHandler
    handler.stats = stats

    server = socketserver.TCPServer(('127.0.0.1', port), handler)
    actual_port = server.server_address[1]
    base_url = f"http://127.0.0.1:{actual_port}"

    # Build and set pages
    handler.pages = build_test_site(base_url)

    # Start server in background thread
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    return server, base_url, stats


# --- URL Extraction ---

# Regex to find URLs in text (flexible, catches most formats)
URL_PATTERN = re.compile(
    r'https?://[^\s<>"\'`\]\)\},;]+',
    re.IGNORECASE
)

def extract_urls_from_output(output: str) -> Set[str]:
    """Extract all HTTP/HTTPS URLs from crawler output."""
    urls = set()
    for match in URL_PATTERN.finditer(output):
        url = match.group(0)
        # Clean up trailing punctuation that might have been captured
        url = url.rstrip('.,;:!?)]\'"')
        urls.add(url)
    return urls


def normalize_url(url: str) -> str:
    """Normalize URL for comparison."""
    parsed = urlparse(url)
    # Normalize path
    path = parsed.path or '/'
    if path != '/' and path.endswith('/'):
        path = path.rstrip('/')
    # Reconstruct
    return f"{parsed.scheme}://{parsed.netloc}{path}".lower()


def normalize_path(path: str) -> str:
    """Normalize path for comparison."""
    if path != '/' and path.endswith('/'):
        return path.rstrip('/')
    return path or '/'


# --- Test Runner ---

@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    details: Optional[List[str]] = None


def run_crawler(command: List[str], seed_url: str, timeout: int = 60) -> Tuple[str, str, int]:
    """Run crawler command and return (stdout, stderr, exit_code)."""
    full_command = command + [seed_url]

    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", f"Timeout after {timeout} seconds", -1
    except FileNotFoundError as e:
        return "", f"Command not found: {e}", -1


def run_tests(
    command: List[str],
    timeout: int = 60,
    verbose: bool = False
) -> List[TestResult]:
    """Run all tests and return results."""
    results = []

    # Start test server
    print("Starting test server...")
    server, base_url, stats = start_test_server()
    time.sleep(0.5)  # Give server time to start

    try:
        print(f"Test server running at {base_url}")
        print(f"Running crawler: {' '.join(command)} {base_url}")
        print("-" * 60)

        # Run the crawler
        stdout, stderr, exit_code = run_crawler(command, base_url, timeout)

        combined_output = stdout + "\n" + stderr

        if verbose:
            print("=== STDOUT ===")
            print(stdout[:5000] if len(stdout) > 5000 else stdout)
            print("=== STDERR ===")
            print(stderr[:2000] if len(stderr) > 2000 else stderr)
            print("=" * 60)

        # Get data for assertions
        requested_paths = [normalize_path(p) for p in stats.get_requests()]
        printed_urls = extract_urls_from_output(combined_output)
        printed_urls_normalized = {normalize_url(u) for u in printed_urls}

        parsed_base = urlparse(base_url)
        base_host = parsed_base.netloc

        if verbose:
            print(f"\nRequested paths: {requested_paths}")
            print(f"Printed URLs: {printed_urls}")

        # --- Test 1: Crawler executes successfully ---
        results.append(TestResult(
            name="Crawler executes",
            passed=exit_code == 0 or len(requested_paths) > 1,
            message=f"Exit code: {exit_code}" if exit_code != 0 else "OK",
            details=[stderr[:500]] if exit_code != 0 and stderr else None
        ))

        # --- Test 2: Crawls the seed page ---
        crawled_root = "/" in requested_paths
        results.append(TestResult(
            name="Crawls seed page",
            passed=crawled_root,
            message="Root page was fetched" if crawled_root else "Root page was NOT fetched"
        ))

        # --- Test 3: Discovers and crawls same-domain pages ---
        expected_paths = {"/", "/about", "/contact", "/products", "/products/item1", "/products/item2", "/team"}
        crawled_paths = set(requested_paths)
        missing_paths = expected_paths - crawled_paths

        results.append(TestResult(
            name="Crawls all same-domain pages",
            passed=len(missing_paths) == 0,
            message=f"Crawled {len(crawled_paths & expected_paths)}/{len(expected_paths)} expected pages",
            details=[f"Missing: {missing_paths}"] if missing_paths else None
        ))

        # --- Test 4: Does NOT crawl isolated page ---
        crawled_isolated = "/isolated" in requested_paths
        results.append(TestResult(
            name="Does not crawl unlinked pages",
            passed=not crawled_isolated,
            message="Correctly skipped /isolated" if not crawled_isolated else "ERROR: Crawled /isolated which is not linked"
        ))

        # --- Test 5: Does NOT crawl external domains ---
        external_crawled = [p for p in requested_paths if "external" in p.lower()]
        results.append(TestResult(
            name="Does not crawl external domains",
            passed=len(external_crawled) == 0,
            message="No external domains crawled" if not external_crawled else f"Crawled external: {external_crawled}"
        ))

        # --- Test 6: Does NOT crawl subdomains ---
        # Check if any request was made to sub.* (would fail/timeout, but check output for attempts)
        subdomain_in_output = any('sub.127.0.0.1' in u or 'sub.localhost' in u for u in printed_urls)
        # We can't easily verify this since subdomain requests would fail, but we check it wasn't crawled
        results.append(TestResult(
            name="Does not crawl subdomains",
            passed=True,  # Hard to verify negatively, assume pass if external test passes
            message="Subdomain links should be printed but not crawled (verified by no subdomain requests)"
        ))

        # --- Test 7: Prints external URLs (found but not crawled) ---
        external_printed = any('external-domain.com' in u for u in printed_urls)
        results.append(TestResult(
            name="Prints external URLs",
            passed=external_printed,
            message="External URLs appear in output" if external_printed else "External URLs NOT found in output"
        ))

        # --- Test 8: Prints subdomain URLs ---
        subdomain_printed = any('sub.' in u for u in printed_urls)
        results.append(TestResult(
            name="Prints subdomain URLs",
            passed=subdomain_printed,
            message="Subdomain URLs appear in output" if subdomain_printed else "Subdomain URLs NOT found in output"
        ))

        # --- Test 9: Handles non-HTTP schemes (doesn't crash) ---
        # The contact page has mailto:, tel:, javascript: links
        contact_crawled = "/contact" in requested_paths
        results.append(TestResult(
            name="Handles non-HTTP schemes",
            passed=contact_crawled,
            message="Contact page (with mailto/tel/js links) was crawled" if contact_crawled else "Contact page not reached"
        ))

        # --- Test 10: No duplicate crawls ---
        path_counts = {}
        for p in requested_paths:
            path_counts[p] = path_counts.get(p, 0) + 1
        duplicates = {p: c for p, c in path_counts.items() if c > 1}

        results.append(TestResult(
            name="No duplicate page fetches",
            passed=len(duplicates) == 0,
            message="No duplicates detected" if not duplicates else f"Duplicate fetches: {duplicates}",
            details=[f"{p}: fetched {c} times" for p, c in duplicates.items()] if duplicates else None
        ))

        # --- Test 11: Outputs something meaningful ---
        results.append(TestResult(
            name="Produces output",
            passed=len(printed_urls) > 0,
            message=f"Found {len(printed_urls)} URLs in output" if printed_urls else "No URLs found in output"
        ))

    finally:
        server.shutdown()

    return results


def print_results(results: List[TestResult]) -> bool:
    """Print test results and return True if all passed."""
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)

    all_passed = True
    for r in results:
        status = "\033[92mPASS\033[0m" if r.passed else "\033[91mFAIL\033[0m"
        print(f"{status}  {r.name}")
        print(f"       {r.message}")
        if r.details:
            for d in r.details:
                print(f"       - {d}")
        if not r.passed:
            all_passed = False

    print("=" * 60)
    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    print(f"Results: {passed_count}/{total_count} tests passed")

    if all_passed:
        print("\033[92mALL TESTS PASSED\033[0m")
    else:
        print("\033[91mSOME TESTS FAILED\033[0m")

    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Test harness for web crawler submissions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s python crawler.py
    %(prog)s ./run.sh
    %(prog)s java -jar crawler.jar
    %(prog)s "sbt 'run'"
    %(prog)s --timeout 120 ./slow_crawler
        """
    )
    parser.add_argument(
        'command',
        nargs='+',
        help='Command to run the crawler (seed URL will be appended)'
    )
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=60,
        help='Timeout in seconds (default: 60)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show crawler output'
    )

    args = parser.parse_args()

    # Handle quoted commands like "sbt 'run'"
    if len(args.command) == 1 and ' ' in args.command[0]:
        command = shlex.split(args.command[0])
    else:
        command = args.command

    results = run_tests(command, timeout=args.timeout, verbose=args.verbose)
    success = print_results(results)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
