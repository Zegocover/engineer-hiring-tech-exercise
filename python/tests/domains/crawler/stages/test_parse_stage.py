from domains.crawler.models import FetchResult
from domains.crawler.stages.parse_stage import DefaultParseStage


class FakeExtractor:
    """Returns a fixed list of raw hrefs, ignoring the HTML."""

    def __init__(self, hrefs: list[str]) -> None:
        self._hrefs = hrefs

    def extract(self, html: str, base_url: str) -> list[str]:
        return list(self._hrefs)


def _html_result(url: str) -> FetchResult:
    return FetchResult(
        requested_url=url,
        final_url=url,
        status=200,
        content_type="text/html",
        html="<html></html>",
        error=None,
    )


async def test_links_are_normalized_sorted_and_deduped() -> None:
    extractor = FakeExtractor(["/b", "/a", "/a#frag", "mailto:x@a.com"])
    stage = DefaultParseStage(extractor=extractor, seed_host="a.com")
    outcome = await stage.parse(_html_result("http://a.com/"))
    # mailto dropped; /a and /a#frag collapse; sorted.
    assert outcome.page.links == ("http://a.com/a", "http://a.com/b")


async def test_on_host_vs_offsite_classification() -> None:
    extractor = FakeExtractor(["http://a.com/p", "http://www.a.com/q", "http://b.com/r"])
    stage = DefaultParseStage(extractor=extractor, seed_host="a.com")
    outcome = await stage.parse(_html_result("http://a.com/"))
    # All three are listed on the page...
    assert outcome.page.links == (
        "http://a.com/p",
        "http://b.com/r",
        "http://www.a.com/q",
    )
    # ...but only the exact-host one is an enqueue candidate (subdomain excluded).
    assert outcome.on_host_links == ("http://a.com/p",)


async def test_links_resolved_against_final_url_after_redirect() -> None:
    extractor = FakeExtractor(["/x"])
    stage = DefaultParseStage(extractor=extractor, seed_host="a.com")
    result = FetchResult(
        requested_url="http://a.com/old",
        final_url="http://a.com/new/page",
        status=200,
        content_type="text/html",
        html="<html></html>",
        error=None,
    )
    outcome = await stage.parse(result)
    assert outcome.page.links == ("http://a.com/x",)
    assert outcome.page.url == "http://a.com/new/page"


async def test_non_html_yields_empty_links_and_no_candidates() -> None:
    extractor = FakeExtractor(["/should-not-be-used"])
    stage = DefaultParseStage(extractor=extractor, seed_host="a.com")
    result = FetchResult(
        requested_url="http://a.com/file.pdf",
        final_url="http://a.com/file.pdf",
        status=200,
        content_type="application/pdf",
        html=None,
        error=None,
    )
    outcome = await stage.parse(result)
    assert outcome.page.links == ()
    assert outcome.on_host_links == ()


async def test_error_result_passes_through_with_no_links() -> None:
    extractor = FakeExtractor([])
    stage = DefaultParseStage(extractor=extractor, seed_host="a.com")
    result = FetchResult(
        requested_url="http://a.com/boom",
        final_url="http://a.com/boom",
        status=None,
        content_type=None,
        html=None,
        error="timeout",
    )
    outcome = await stage.parse(result)
    assert outcome.page.error == "timeout"
    assert outcome.page.links == ()
    assert outcome.on_host_links == ()
