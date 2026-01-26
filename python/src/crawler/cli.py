"""Command-line interface for the crawler application."""

import argparse
import logging

from crawler import app, config, urls


def parse_base_url(value: str) -> str:
    """Validate the base URL from the CLI."""
    try:
        urls.validate_base_url(value)
        return value
    except urls.UrlParsingError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crawler")
    output_group = parser.add_argument_group("Output")
    crawl_group = parser.add_argument_group("Crawl options")
    parser.add_argument(
        "base_url",
        type=parse_base_url,
        help="Starting URL to crawl (http/https).",
    )
    crawl_group.add_argument(
        "--profile",
        choices=[
            config.PROFILE_CONSERVATIVE,
            config.PROFILE_BALANCED,
            config.PROFILE_AGGRESSIVE,
        ],
        default=config.PROFILE_BALANCED,
        help=(
            "Preset crawl limits (max pages/depth, concurrency, "
            "timeouts, rate)."
        ),
    )
    output_group.add_argument(
        "--output",
        choices=[config.OUTPUT_TEXT, config.OUTPUT_JSON],
        default=config.OUTPUT_TEXT,
        help="Output format (written to a file).",
    )
    output_group.add_argument(
        "--output-file",
        default=None,
        help=(
            "Output file path; defaults to output.txt or output.json "
            "based on format."
        ),
    )
    crawl_group.add_argument(
        "--robots",
        choices=[config.ROBOTS_RESPECT, config.ROBOTS_IGNORE],
        default=config.ROBOTS_RESPECT,
        help="Whether to respect robots.txt rules.",
    )
    crawl_group.add_argument(
        "--user-agent",
        default="crawler/1.0",
        help="User-Agent header value for HTTP requests.",
    )
    crawl_group.add_argument(
        "--strip-fragments",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Strip #fragments from extracted links (default: true).",
    )
    crawl_group.add_argument(
        "--only-http-links",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Only include http/https links in output (default: true).",
    )
    crawl_group.add_argument(
        "--only-in-scope-links",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Only include in-scope links in output (default: false).",
    )
    crawl_group.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    logging.info("🕷️ Starting crawler")
    cfg = config.config_from_args(args)
    logging.debug("✅ Parsed config: %s", cfg)
    return app.run(cfg)
