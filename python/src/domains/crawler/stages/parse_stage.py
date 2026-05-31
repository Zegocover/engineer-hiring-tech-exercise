"""Stage 2: turn a FetchResult into a PageResult + on-host enqueue candidates."""

from domains.crawler.models import FetchResult, PageResult, ParseOutcome
from domains.crawler.ports import LinkExtractor
from domains.crawler.urls import normalize, same_host


class DefaultParseStage:
    """Extract links, normalize them, and split on-host from off-site.

    Depends only on the LinkExtractor port, so the HTML parser is swappable.
    """

    def __init__(self, extractor: LinkExtractor, seed_host: str) -> None:
        self._extractor = extractor
        self._seed_host = seed_host

    async def parse(self, result: FetchResult) -> ParseOutcome:
        if result.html is None:
            page = PageResult(
                url=result.final_url,
                links=(),
                status=result.status,
                error=result.error,
            )
            return ParseOutcome(page=page, on_host_links=())

        normalized: set[str] = set()
        for href in self._extractor.extract(result.html, result.final_url):
            canonical = normalize(href, result.final_url)
            if canonical is not None:
                normalized.add(canonical)

        all_links = tuple(sorted(normalized))
        on_host = tuple(u for u in all_links if same_host(u, self._seed_host))
        page = PageResult(
            url=result.final_url,
            links=all_links,
            status=result.status,
            error=result.error,
        )
        return ParseOutcome(page=page, on_host_links=on_host)
