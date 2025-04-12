from dataclasses import dataclass, field


@dataclass
class PageReport:
    url: str
    status: int
    links: list[str] = field(default_factory=list)


@dataclass
class SiteReport:
    pages: list[PageReport] = field(default_factory=list)


@dataclass
class FetchResult:
    url: str
    status: int
    text: str | None
