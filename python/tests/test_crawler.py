"""BDD-style tests: test_given_<context>_when_<action>_then_<outcome>.

No real network anywhere — every test drives the crawler through an
httpx.MockTransport fake site.
"""

import asyncio
import logging
import urllib.robotparser

import httpx
import pytest

from crawler import USER_AGENT, Crawler, Fetcher, FetchError, extract_links, load_robots, main

BASE = "https://site.test"


def page(*links: str) -> httpx.Response:
    body = "".join(f'<a href="{link}">x</a>' for link in links)
    return httpx.Response(200, html=f"<html><body>{body}</body></html>")


def make_client(routes: dict) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        route = routes.get(str(request.url))
        if route is None:
            return httpx.Response(404, text="not found")
        return route(request) if callable(route) else route

    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True)


def crawl(routes: dict, robots: str | None = None, **kwargs) -> list[str]:
    """Run a full crawl against a fake site and return the printed page blocks."""
    output: list[str] = []
    robots_parser = None
    if robots is not None:
        robots_parser = urllib.robotparser.RobotFileParser()
        robots_parser.parse(robots.splitlines())

    async def go():
        async with make_client(routes) as client:
            fetcher = Fetcher(client, base_delay=0)
            await Crawler(BASE, fetcher, robots=robots_parser, out=output.append, **kwargs).crawl()

    asyncio.run(go())
    return output


def pages_visited(output: list[str]) -> set[str]:
    return {block.splitlines()[0] for block in output}


# --- link extraction ---


def test_given_relative_links_when_parsed_then_they_become_absolute():
    html = '<a href="/about">a</a><a href="team">b</a>'
    assert extract_links(html, f"{BASE}/jobs/") == [f"{BASE}/about", f"{BASE}/jobs/team"]


def test_given_fragments_duplicates_and_mailto_when_parsed_then_they_are_cleaned():
    html = (
        '<a href="/a#top">1</a><a href="/a#bottom">2</a>'
        '<a href="mailto:hi@x.test">3</a><a href="javascript:void(0)">4</a>'
    )
    assert extract_links(html, BASE) == [f"{BASE}/a"]


# --- fetcher: retries, backoff, captcha ---


def flaky(responses: list[httpx.Response]):
    def handler(request):
        return responses.pop(0)

    return handler


def fetch_with(routes: dict, **fetcher_kwargs):
    async def go():
        async with make_client(routes) as client:
            return await Fetcher(client, base_delay=0, **fetcher_kwargs).fetch(BASE)

    return asyncio.run(go())


def test_given_a_flaky_server_when_fetching_then_it_retries_and_succeeds():
    routes = {BASE: flaky([httpx.Response(500), httpx.Response(503), page("/ok")])}
    assert fetch_with(routes).status_code == 200


def test_given_a_persistently_broken_server_when_fetching_then_it_gives_up():
    routes = {BASE: lambda request: httpx.Response(500)}
    with pytest.raises(FetchError, match="after 3 attempts"):
        fetch_with(routes, max_retries=2)


def test_given_rate_limiting_when_fetching_then_retry_after_is_honoured():
    delays: list[float] = []

    async def record_sleep(seconds):
        delays.append(seconds)

    routes = {BASE: flaky([httpx.Response(429, headers={"retry-after": "7"}), page()])}

    async def go():
        async with make_client(routes) as client:
            await Fetcher(client, base_delay=0, sleep=record_sleep).fetch(BASE)

    asyncio.run(go())
    assert delays and delays[0] >= 7


def test_given_a_captcha_wall_when_fetching_then_it_gives_up_without_retrying():
    calls = []

    def captcha(request):
        calls.append(request)
        return httpx.Response(403, text="<html>Please solve this CAPTCHA</html>")

    with pytest.raises(FetchError, match="captcha"):
        fetch_with({BASE: captcha})
    assert len(calls) == 1


# --- crawler behaviour ---


def test_given_a_small_site_when_crawled_then_every_page_prints_once_with_its_links():
    routes = {
        BASE: page("/a", "/b"),
        f"{BASE}/a": page("/b", "https://elsewhere.test/x"),
        f"{BASE}/b": page("/"),
    }
    output = crawl(routes)
    assert pages_visited(output) == {BASE, f"{BASE}/a", f"{BASE}/b"}
    a_block = next(block for block in output if block.startswith(f"{BASE}/a"))
    assert "https://elsewhere.test/x" in a_block  # external links are printed...


def test_given_external_and_subdomain_links_when_crawled_then_they_are_not_followed():
    routes = {
        BASE: page("https://elsewhere.test/x", "https://sub.site.test/y", "/here"),
        f"{BASE}/here": page(),
    }
    output = crawl(routes)
    assert pages_visited(output) == {BASE, f"{BASE}/here"}  # ...but never crawled


def test_given_a_broken_link_when_crawled_then_the_crawl_continues():
    routes = {BASE: page("/missing", "/fine"), f"{BASE}/fine": page()}
    assert pages_visited(crawl(routes)) == {BASE, f"{BASE}/fine"}


def test_given_a_non_html_resource_when_crawled_then_it_is_not_parsed():
    routes = {
        BASE: page("/report.pdf"),
        f"{BASE}/report.pdf": httpx.Response(
            200, content=b"%PDF", headers={"content-type": "application/pdf"}
        ),
    }
    assert pages_visited(crawl(routes)) == {BASE}


def test_given_an_off_domain_redirect_when_crawled_then_it_is_not_parsed():
    routes = {
        BASE: page("/leave"),
        f"{BASE}/leave": httpx.Response(302, headers={"location": "https://elsewhere.test/"}),
        "https://elsewhere.test/": page("/trap"),
    }
    assert pages_visited(crawl(routes)) == {BASE}


def test_given_a_base_url_that_redirects_to_www_when_crawled_then_it_fails_loudly(caplog):
    routes = {
        BASE: httpx.Response(301, headers={"location": "https://www.site.test/"}),
        "https://www.site.test/": page("/trap"),
    }
    with caplog.at_level(logging.ERROR, logger="crawler"):
        output = crawl(routes)
    assert output == []  # www. is a subdomain, so nothing is in scope...
    assert "redirects off-host to https://www.site.test/" in caplog.text  # ...but we say so


def test_given_a_forbidden_robots_txt_when_loaded_then_everything_is_disallowed():
    routes = {f"{BASE}/robots.txt": httpx.Response(403, text="forbidden")}

    async def go():
        async with make_client(routes) as client:
            return await load_robots(client, BASE)

    parser = asyncio.run(go())
    assert not parser.can_fetch(USER_AGENT, f"{BASE}/anything")


def test_given_a_robots_disallow_when_crawled_then_the_page_is_skipped():
    routes = {BASE: page("/private", "/public"), f"{BASE}/public": page()}
    robots = "User-agent: *\nDisallow: /private\n"
    assert pages_visited(crawl(routes, robots=robots)) == {BASE, f"{BASE}/public"}


def test_given_a_max_pages_limit_when_crawled_then_the_crawl_stops_there():
    routes = {f"{BASE}/{i}" if i else BASE: page(f"/{i + 1}") for i in range(10)}
    assert len(crawl(routes, max_pages=3)) == 3


# --- CLI validation ---


def test_given_a_relative_url_when_run_from_the_cli_then_it_exits_with_an_error():
    with pytest.raises(SystemExit):
        main(["not-a-url"])


def test_given_a_zero_concurrency_when_run_from_the_cli_then_it_exits_with_an_error():
    with pytest.raises(SystemExit):
        main(["--concurrency", "0", BASE])
