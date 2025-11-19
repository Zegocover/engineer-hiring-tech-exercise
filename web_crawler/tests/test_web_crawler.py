import pytest
import aiohttp
import asyncio
import time
from urllib.parse import urlparse
from web_crawler import WebCrawler


@pytest.mark.asyncio
async def test_crawl_simple_site_visits(make_server):
    async def handler_root(request):
        return aiohttp.web.Response(text='<a href="/a">A</a><a href="/b">B</a>')

    async def handler_a(request):
        return aiohttp.web.Response(text='<a href="/">Root</a>')

    server, url = await make_server({'/': handler_root, '/a': handler_a})
    c = WebCrawler(url, concurrency=2, max_pages=10)
    await c.crawl()

    # assert the crawler visited the root and linked pages
    assert f"{url}/" in c.visited
    assert f"{url}/a" in c.visited
    assert f"{url}/b" in c.visited


@pytest.mark.asyncio
async def test_prints_page_visited_and_links_found(make_server, capsys):
    # root page links to three pages; crawler should print the Visited line and the three links
    async def root(request):
        host = request.host
        base = f"http://{host}:{request.url.port}"
        links = ''.join(f'<a href="/p{i}">p{i}</a>' for i in range(1, 4))
        return aiohttp.web.Response(text=links)

    async def page(request):
        return aiohttp.web.Response(text='<html></html>')

    server, base = await make_server({'/': root, r'/p{tail:\d+}': page, r'/{tail:.*}': page})
    c = WebCrawler(base, concurrency=1, max_pages=4)
    await c.crawl()

    out = capsys.readouterr().out

    # Expect a Visited line for the root page
    assert f"Visited: {base}/" in out

    # Expect the three absolute links to appear under Links
    expected_links = [f"{base}/p{i}" for i in range(1, 4)]
    for l in expected_links:
        assert f" - {l}" in out


@pytest.mark.asyncio
async def test_skips_external_domains(make_server):
    # root links to an internal page and an external domain; crawler must not visit external domain
    async def root(request):
        return aiohttp.web.Response(text='<a href="/ok">ok</a><a href="http://example.com/external">ext</a>')

    async def ok(request):
        return aiohttp.web.Response(text='<html></html>')

    server, base = await make_server({'/': root, '/ok': ok})
    c = WebCrawler(base, concurrency=2, max_pages=5)
    await c.crawl()

    # internal page must be visited (use exact absolute URL)
    assert f"{base}/ok" in c.visited
    # external domain must not be visited (compare hostnames)
    assert all(urlparse(visited_url).hostname != 'example.com' for visited_url in c.visited)


@pytest.mark.asyncio
async def test_skips_subdomain_links(make_server):
    async def handler_root(request):
        host = request.host
        # link to a subdomain of the test host (should be considered different hostname)
        sub = f"http://sub.{host}/other"
        return aiohttp.web.Response(text=f'<a href="/ok">ok</a><a href="{sub}">sub</a>')

    async def handler_ok(request):
        return aiohttp.web.Response(text='ok')

    server, base = await make_server({'/': handler_root, '/ok': handler_ok})

    c = WebCrawler(base, concurrency=3, max_pages=10)
    await c.crawl()

    # ensure only same-host path /ok was visited, not the subdomain link
    assert any(u.endswith('/ok') for u in c.visited)
    assert all('sub.' not in u for u in c.visited)


@pytest.mark.asyncio
async def test_canonical_preference(make_server):
    async def handler_root(request):
        return aiohttp.web.Response(text='<link rel="canonical" href="/canonical" /><a href="/child">c</a>')

    async def handler_canonical(request):
        return aiohttp.web.Response(text='<a href="/child2">c2</a>')

    server, base = await make_server({'/': handler_root, '/canonical': handler_canonical})

    c = WebCrawler(base, concurrency=2, max_pages=10)
    await c.crawl()
    assert f"{base}/canonical" in c.visited


@pytest.mark.asyncio
async def test_canonical_collision(make_server):
    calls = {"canon": 0}
    async def a(request):
        return aiohttp.web.Response(text='<link rel="canonical" href="/canon" /><a href="/b">b</a>')

    async def b(request):
        return aiohttp.web.Response(text='<link rel="canonical" href="/canon" /><a href="/a">a</a>')

    async def canon(request):
        calls["canon"] += 1
        return aiohttp.web.Response(text='<a href="/done">done</a>')

    async def done(request):
        return aiohttp.web.Response(text='done')

    server, base_root = await make_server({'/a': a, '/b': b, '/canon': canon, '/done': done})
    base = f"http://{server.host}:{server.port}/a"

    c = WebCrawler(base, concurrency=3, max_pages=10)
    await c.crawl()

    canon_url = f"http://{server.host}:{server.port}/canon"
    assert canon_url in c.visited
    assert calls["canon"] == 1
    # canonical's downstream link made it:
    assert f"http://{server.host}:{server.port}/done" in c.visited


@pytest.mark.asyncio
async def test_honour_crawl_delay_from_robots(make_server):
    crawl_delay = 0.25
    page_request_times = []

    async def robots(request):
        text = f"User-agent: *\nCrawl-delay: {crawl_delay}\n"
        return aiohttp.web.Response(text=text)

    async def page(request):
        page_request_times.append(time.time())
        return aiohttp.web.Response(text="<html></html>")

    server, base = await make_server({'/robots.txt': robots, '/': page})

    c = WebCrawler(base, concurrency=4, max_pages=3)
    await c.crawl()

    if len(page_request_times) >= 2:
        diffs = [t2 - t1 for t1, t2 in zip(page_request_times, page_request_times[1:])]
        assert all(d >= (crawl_delay) for d in diffs)


@pytest.mark.asyncio
async def test_retry_on_transient_error(make_server):
    # Handler that fails twice then succeeds
    calls = {"count": 0}

    async def unstable(request):
        calls['count'] += 1
        if calls['count'] < 3:
            return aiohttp.web.Response(status=500, text="temporary")
        return aiohttp.web.Response(text='<a href="/">root</a>')

    server, base = await make_server({'/unstable': unstable})

    c = WebCrawler(base + '/unstable', concurrency=2, max_pages=5)
    await c.crawl()

    # ensure the unstable page was eventually visited
    assert any('/unstable' in v for v in c.visited)


@pytest.mark.asyncio
async def test_retry_backoff(make_server):
    state = {"count": 0}

    async def flaky(request):
        state['count'] += 1
        if state['count'] < 3:
            return aiohttp.web.Response(status=500, text='err')
        return aiohttp.web.Response(text='<a href="/done">done</a>')

    async def done_h(request):
        return aiohttp.web.Response(text='done')

    server, base = await make_server({'/': flaky, '/done': done_h})

    c = WebCrawler(base, concurrency=1, max_pages=10)
    await c.crawl()
    assert any(u.endswith("/done") for u in c.visited)



@pytest.mark.asyncio
async def test_tracking_blacklist(make_server):
    # link contains a blacklisted tracking param `ref` which should be stripped
    async def root(request):
        return aiohttp.web.Response(text='<a href="/p?ref=123&keep=1">p</a>')

    async def p(request):
        return aiohttp.web.Response(text='<html></html>')

    server, base = await make_server({'/': root, '/p': p})

    c = WebCrawler(base, concurrency=1, max_pages=5, tracking_blacklist=['ref'])
    await c.crawl()

    # expect the `ref` param to be removed and `keep=1` preserved
    assert f"{base}/p?keep=1" in c.visited


@pytest.mark.asyncio
async def test_tracking_whitelist(make_server):
    # utm_source is normally stripped; when whitelisted it should be preserved
    async def root(request):
        return aiohttp.web.Response(text='<a href="/q?utm_source=abc&keep=2">q</a>')

    async def q(request):
        return aiohttp.web.Response(text='<html></html>')

    server, base = await make_server({'/': root, '/q': q})

    c = WebCrawler(base, concurrency=1, max_pages=5, tracking_whitelist=['utm_source'])
    await c.crawl()

    # Expect both keep and utm_source to be preserved (sorted order yields keep first)
    assert f"{base}/q?keep=2&utm_source=abc" in c.visited

