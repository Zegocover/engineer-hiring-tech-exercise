from domains.crawler.models import FetchResult
from domains.crawler.stages.parse_stage import DefaultParseStage


def _html_result(url: str, html: str) -> FetchResult:
    return FetchResult(
        requested_url=url,
        final_url=url,
        status=200,
        content_type="text/html",
        html=html,
        error=None,
    )


async def test_links_are_normalized_sorted_and_deduped() -> None:
    html = (
        '<a href="/b">b</a><a href="/a">a</a>'
        '<a href="/a#frag">a-frag</a><a href="mailto:x@a.com">mail</a>'
    )
    stage = DefaultParseStage(seed_host="a.com")
    outcome = await stage.parse(_html_result("http://a.com/", html))
    # mailto dropped; /a and /a#frag collapse; sorted.
    assert outcome.page.links == ("http://a.com/a", "http://a.com/b")


async def test_on_host_vs_offsite_classification() -> None:
    html = (
        '<a href="http://a.com/p">p</a>'
        '<a href="http://www.a.com/q">q</a>'
        '<a href="http://b.com/r">r</a>'
    )
    stage = DefaultParseStage(seed_host="a.com")
    outcome = await stage.parse(_html_result("http://a.com/", html))
    # All three are listed on the page...
    assert outcome.page.links == (
        "http://a.com/p",
        "http://b.com/r",
        "http://www.a.com/q",
    )
    # ...but only the exact-host one is an enqueue candidate (subdomain excluded).
    assert outcome.on_host_links == ("http://a.com/p",)


async def test_links_resolved_against_final_url_after_redirect() -> None:
    stage = DefaultParseStage(seed_host="a.com")
    # href="x" is page-relative; it must resolve against final_url's directory
    # (/new/), not the requested_url (/old). So the result is /new/x, proving the
    # parse stage uses final_url.
    result = FetchResult(
        requested_url="http://a.com/old",
        final_url="http://a.com/new/page",
        status=200,
        content_type="text/html",
        html='<a href="x">x</a>',
        error=None,
    )
    outcome = await stage.parse(result)
    assert outcome.page.links == ("http://a.com/new/x",)
    assert outcome.page.url == "http://a.com/new/page"


async def test_non_html_yields_empty_links_and_no_candidates() -> None:
    stage = DefaultParseStage(seed_host="a.com")
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
    stage = DefaultParseStage(seed_host="a.com")
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
