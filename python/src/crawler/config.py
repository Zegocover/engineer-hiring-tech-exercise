from pathlib import Path

# The token we send as User-Agent and the one we match robots.txt rules
# against. These must stay the same string, or we would honour rules written
# for an agent we do not actually identify as.
USER_AGENT = "PoliteAragog/1.0"

# Per-request timeout, distinct from the whole-crawl budget the CLI/TUI
# pass to Crawler.crawl as `timeout`.
DEFAULT_REQUEST_TIMEOUT = 30.0

# Where per-domain crawl results are written. Relative to the working
# directory, so it follows wherever the CLI/TUI is invoked from.
DEFAULT_OUTPUT_DIR = Path("output")

DEFAULT_MAX_CONCURRENCY = 10
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 0.5
DEFAULT_BACKOFF_MAX = 10.0
RETRYABLE_STATUS_CODES = {429, 502, 503, 504}
