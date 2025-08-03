import subprocess
import http.server
import threading
import os
import time
import sys

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "../fixtures")


def run_test_server(directory, port):
    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.ThreadingHTTPServer(("localhost", port), handler)
    os.chdir(directory)
    httpd.serve_forever()


def test_cli_crawls_html_links():
    port = 8001
    server_thread = threading.Thread(
        target=run_test_server, args=(FIXTURES_DIR, port), daemon=True
    )
    server_thread.start()
    time.sleep(1)  # Wait for server to start

    main_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../src/__main__.py")
    )
    url = f"http://localhost:{port}/"
    result = subprocess.run(
        [sys.executable, main_path, url, "--threads", "1"],
        capture_output=True,
        text=True,
    )
    assert (
        """http://localhost:8001/
- http://localhost:8001/page1.html
- http://localhost:8001/page2.html
http://localhost:8001/page1.html
- http://localhost:8001/
- http://www.google.com
http://localhost:8001/page2.html
- http://localhost:8001/
- http://localhost:8001/not-found.html
http://localhost:8001/not-found.html
"""
        == result.stdout
    )
    assert result.returncode == 0
