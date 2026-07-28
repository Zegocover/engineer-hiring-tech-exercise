"""Serialises a CrawlResult to a JSON file, one file per crawled domain.

Kept separate from the CLI/TUI so both entry points emit an identical
document, and so the shape is easy to point at a real datastore later.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from crawler.config import DEFAULT_OUTPUT_DIR
from crawler.crawler import CrawlResult


def build_document(result: CrawlResult, start_url: str) -> dict:
    """Builds the JSON-serialisable record for a single crawl.

    Sets are sorted into lists so the file is deterministic and diffable
    between runs; `json` cannot encode a set regardless.
    """
    return {
        "domain": urlsplit(start_url).netloc,
        "start_url": start_url,
        "crawled_at": datetime.now(UTC).isoformat(),
        "completed": result.completed,
        "visited": sorted(result.visited),
        "found_urls_by_domain": {
            domain: sorted(urls)
            for domain, urls in sorted(result.found_urls_by_domain.items())
        },
    }


def write_result(
    result: CrawlResult,
    start_url: str,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    """Writes the crawl to `<output_dir>/<domain>.json` and returns the path.

    Re-crawling a domain replaces its file, so the directory always holds
    the latest run per domain.
    """
    document = build_document(result, start_url)
    output_dir.mkdir(parents=True, exist_ok=True)

    path = output_dir / f"{_filename_for(document['domain'])}.json"
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def _filename_for(domain: str) -> str:
    """Makes a domain safe to use as a filename.

    A netloc can carry a port (`localhost:8000`) or credentials, and `:`
    and `/` are not portable in filenames, so they are replaced rather
    than allowed to escape the output directory.
    """
    safe = domain.replace(":", "_").replace("/", "_").replace("\\", "_")
    return safe or "unknown"
