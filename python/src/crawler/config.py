"""Configuration models for the crawler."""

from dataclasses import dataclass
from typing import Final, Literal

PROFILE_CONSERVATIVE: Final = "conservative"
PROFILE_BALANCED: Final = "balanced"
PROFILE_AGGRESSIVE: Final = "aggressive"

OUTPUT_TEXT: Final = "text"
OUTPUT_JSON: Final = "json"

ROBOTS_RESPECT: Final = "respect"
ROBOTS_IGNORE: Final = "ignore"


ProfileName = Literal[
    PROFILE_CONSERVATIVE,
    PROFILE_BALANCED,
    PROFILE_AGGRESSIVE,
]
OutputFormat = Literal[OUTPUT_TEXT, OUTPUT_JSON]
RobotsMode = Literal[ROBOTS_RESPECT, ROBOTS_IGNORE]

DEFAULT_OUTPUT_FILES: dict[OutputFormat, str] = {
    OUTPUT_TEXT: "output.txt",
    OUTPUT_JSON: "output.json",
}


@dataclass(frozen=True)
class CrawlProfile:
    name: ProfileName
    max_pages_crawled: int
    max_depth: int
    concurrency: int
    timeout_seconds: int
    max_attempts: int


PROFILE_SETTINGS: dict[ProfileName, dict[str, int]] = {
    PROFILE_CONSERVATIVE: {
        "max_pages_crawled": 500,
        "max_depth": 3,
        "concurrency": 10,
        "timeout_seconds": 10,
        "max_attempts": 3,
    },
    PROFILE_BALANCED: {
        "max_pages_crawled": 2000,
        "max_depth": 5,
        "concurrency": 25,
        "timeout_seconds": 10,
        "max_attempts": 3,
    },
    PROFILE_AGGRESSIVE: {
        "max_pages_crawled": 10000,
        "max_depth": 8,
        "concurrency": 50,
        "timeout_seconds": 8,
        "max_attempts": 3,
    },
}

PROFILES: dict[ProfileName, CrawlProfile] = {
    name: CrawlProfile(name=name, **settings)
    for name, settings in PROFILE_SETTINGS.items()
}


@dataclass(frozen=True)
class CrawlerConfig:
    base_url: str
    profile: CrawlProfile
    output_format: OutputFormat
    output_file: str
    robots: RobotsMode
    user_agent: str
    strip_fragments: bool
    only_http_links: bool
    only_in_scope_links: bool
    verbose: bool


def config_from_args(args) -> CrawlerConfig:
    profile = PROFILES[args.profile]
    output_file = args.output_file
    if output_file is None:
        output_file = DEFAULT_OUTPUT_FILES[args.output]

    return CrawlerConfig(
        base_url=args.base_url,
        profile=profile,
        output_format=args.output,
        output_file=output_file,
        robots=args.robots,
        user_agent=args.user_agent,
        strip_fragments=args.strip_fragments,
        only_http_links=args.only_http_links,
        only_in_scope_links=args.only_in_scope_links,
        verbose=args.verbose,
    )
