from domains.crawler.models import FetchResult
from domains.crawler.stages.fetch_stage import DefaultFetchStage


class RecordingFetcher:
    """Records calls and returns a canned 200 HTML result."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def fetch(self, url: str) -> FetchResult:
        self.calls.append(url)
        return FetchResult(
            requested_url=url,
            final_url=url,
            status=200,
            content_type="text/html",
            html="<html></html>",
            error=None,
        )


class AllowAll:
    async def allowed(self, url: str) -> bool:
        return True


class DenyAll:
    async def allowed(self, url: str) -> bool:
        return False


async def test_allowed_url_is_fetched() -> None:
    fetcher = RecordingFetcher()
    stage = DefaultFetchStage(fetcher=fetcher, robots=AllowAll())
    result = await stage.fetch("http://a.com/p")
    assert result.status == 200
    assert fetcher.calls == ["http://a.com/p"]


async def test_disallowed_url_is_not_fetched() -> None:
    fetcher = RecordingFetcher()
    stage = DefaultFetchStage(fetcher=fetcher, robots=DenyAll())
    result = await stage.fetch("http://a.com/secret")
    assert fetcher.calls == []
    assert result.html is None
    assert result.error == "disallowed by robots policy"
    assert result.requested_url == "http://a.com/secret"
    assert result.final_url == "http://a.com/secret"
