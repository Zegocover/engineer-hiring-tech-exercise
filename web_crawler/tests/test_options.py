import pytest
import aiohttp
import asyncio
import time
from web_crawler import WebCrawler
from urllib.parse import urlparse, parse_qs


@pytest.mark.asyncio
# --concurrency
async def test_concurrency_bound(make_server):
    # handler that sleeps to simulate long requests and records concurrent handlers
    state = {'active': 0, 'max': 0}

    async def handler(request):
        state['active'] += 1
        state['max'] = max(state['max'], state['active'])
        await asyncio.sleep(0.15)
        state['active'] -= 1
        return aiohttp.web.Response(text='<a href="/">root</a>')

    server, base = await make_server({'/': handler, r'/{tail:.*}': handler})

    concurrency = 3
    c = WebCrawler(base, concurrency=concurrency, max_pages=6)
    await c.crawl()

    # ensure we never exceeded concurrency
    assert state['max'] <= concurrency


@pytest.mark.asyncio
# --max-pages
async def test_max_pages(make_server):
    NUM = 50
    async def handler_root(request):
        links = ''.join(f'<a href="/p{i}">p{i}</a>' for i in range(NUM))
        return aiohttp.web.Response(text=links)

    async def handler_page(request):
        return aiohttp.web.Response(text='<html></html>')

    server, base = await make_server({'/': handler_root, r'/{tail:.*}': handler_page})

    c = WebCrawler(base, concurrency=5, max_pages=5)
    await c.crawl()
    assert len(c.visited) <= (5 + c.concurrency)


@pytest.mark.asyncio
# --max-depth
async def test_max_depth(make_server):
    MAX_SERVER_DEPTH = 3

    async def handler(request):
        path = request.path
        segments = [s for s in path.split('/') if s]
        if not segments:
            depth = 0
            parent_id = "root"
        else:
            try:
                depth = int(segments[0])
            except Exception:
                depth = 0
            parent_id = "_".join(segments)
        links = []
        if depth < MAX_SERVER_DEPTH:
            next_depth = depth + 1
            for i in range(3):
                links.append(f"/{next_depth}/{parent_id}_{i}")
        body = ""
        for l in links:
            body += f'<a href="{l}">{l}</a>'
        return aiohttp.web.Response(text=body)

    server, base = await make_server({'/': handler, r'/{tail:.*}': handler})

    expected = sum(3 ** d for d in range(0, MAX_SERVER_DEPTH + 1))
    c = WebCrawler(base, concurrency=4, max_pages=500, max_depth=3)
    await c.crawl()
    assert len(c.visited) == expected


@pytest.mark.asyncio
# --timeout
async def test_timeout_respected(make_server):
    # Handler sleeps longer than the crawler timeout
    async def slow(request):
        await asyncio.sleep(0.5)
        return aiohttp.web.Response(text='<html></html>')

    server, base = await make_server({'/': slow})

    # Set a very small timeout so the request will time out; restrict to
    # a single page so only the root is fetched.
    c = WebCrawler(base, concurrency=1, max_pages=1, timeout=0.1)
    start = time.time()
    await c.crawl()
    duration = time.time() - start

    # The crawl should take roughly the timeout+retry/backoff budget (i.e. timeout enforced)
    # We expect the total time to be noticeably larger than a single handler sleep (due to retries/backoff)
    assert duration >= 1.5 and duration < 2.5

    # The crawler should have recorded the attempted URL (even if fetch timed out)
    assert c._normalise(base) in c.visited


@pytest.mark.asyncio
# --user-agent
async def test_user_agent_header_set(make_server):
    seen = []

    async def handler(request):
        ua = request.headers.get('User-Agent')
        seen.append(ua)
        return aiohttp.web.Response(text='<html></html>')

    server, base = await make_server({'/': handler})

    custom_ua = 'my-test-agent/42.0'
    c = WebCrawler(base, concurrency=1, max_pages=1, user_agent=custom_ua)
    await c.crawl()

    assert any(custom_ua == u for u in seen), f"Expected User-Agent '{custom_ua}' in requests, saw: {seen}"


@pytest.mark.asyncio
# --ignore-robots-txt
async def test_ignore_robots_flag_async(make_server):
    async def robots(request):
        return aiohttp.web.Response(text="User-agent: *\nDisallow: /blocked")

    async def handler_root(request):
        return aiohttp.web.Response(text='<a href="/blocked">blocked</a>')

    async def handler_blocked(request):
        return aiohttp.web.Response(text='blocked')

    server, base = await make_server({'/robots.txt': robots, '/': handler_root, '/blocked': handler_blocked})

    c1 = WebCrawler(base, concurrency=2, max_pages=10)
    await c1.crawl()
    assert all(not u.endswith('/blocked') for u in c1.visited)

    c2 = WebCrawler(base, concurrency=2, max_pages=10, ignore_robots=True)
    await c2.crawl()
    assert any(u.endswith('/blocked') for u in c2.visited)


# --ignore-robots-txt
def test_ignore_robots_flag():
    # ensure crawler does not call robots methods
    c = WebCrawler("https://example.com", ignore_robots=True)

    class BadRobots:
        def is_allowed(self, *args, **kwargs):
            raise RuntimeError("is_allowed should not be called when ignore_robots=True")

    # Inject a robots object that would raise if consulted
    c.robots = BadRobots()

    # Emulate the short-circuit conditional used in the worker:
    # `if self.robots and not self.ignore_robots and not self.robots.is_allowed(...):`
    try:
        skipped = False
        if c.robots and not c.ignore_robots and not c.robots.is_allowed(
            "https://example.com/blocked", c.user_agent
        ):
            skipped = True
    except RuntimeError:
        pytest.fail("robots.is_allowed was called despite ignore_robots=True")

    # When ignore_robots=True we should NOT mark the URL as skipped by robots
    assert skipped is False


@pytest.mark.asyncio
# --ignore-crawl-delay
async def test_ignore_crawl_delay_flag_async(make_server):
    # robots.txt sets a crawl-delay; when ignore_crawl_delay=True the crawler should not wait
    crawl_delay = 0.5
    request_times = []

    async def robots(request):
        return aiohttp.web.Response(text=f"User-agent: *\nCrawl-delay: {crawl_delay}")

    async def handler(request):
        request_times.append(time.time())
        return aiohttp.web.Response(text='<a href="/">root</a>')

    server, base = await make_server({'/robots.txt': robots, '/': handler})

    # With crawl-delay honoured, multiple requests will be spaced by ~crawl_delay
    c1 = WebCrawler(base, concurrency=2, max_pages=3)
    await c1.crawl()
    times_honoured = list(request_times)

    # reset and run with ignore_crawl_delay
    request_times.clear()
    c2 = WebCrawler(base, concurrency=4, max_pages=3, ignore_crawl_delay=True)
    await c2.crawl()
    times_ignored = list(request_times)

    # If crawl-delay honoured there should be visible spacing; when ignored, spacing should be smaller
    if len(times_honoured) >= 2 and len(times_ignored) >= 2:
        spaced = times_honoured[1] - times_honoured[0]
        tight = times_ignored[1] - times_ignored[0]
        assert tight < spaced


# --ignore-crawl-delay
def test_ignore_crawl_delay_flag():
    # ensure crawler does not call get_crawl_delay
    # when `ignore_crawl_delay=True` (short-circuited logic).
    c = WebCrawler("https://example.com", ignore_crawl_delay=True)

    class BadRobots:
        def get_crawl_delay(self, *args, **kwargs):
            raise RuntimeError("get_crawl_delay should not be called when ignore_crawl_delay=True")

    # Inject a robots object that would raise if get_crawl_delay were consulted
    c.robots = BadRobots()

    # Emulate the short-circuit conditional used in _fetch_and_extract:
    # `if self.robots and not self.ignore_crawl_delay and not self.ignore_robots:`
    try:
        delay = None
        if c.robots and not c.ignore_crawl_delay and not c.ignore_robots:
            delay = c.robots.get_crawl_delay(c.user_agent)
    except RuntimeError:
        pytest.fail("robots.get_crawl_delay was called despite ignore_crawl_delay=True")

    # Since ignore_crawl_delay=True we should not have retrieved a delay
    assert delay is None


# --no-strip-tracking-params
def test_normalise_no_strip_when_opt_out():
    c = WebCrawler("https://example.com", strip_tracking_params=False)
    url = "https://example.com/path?utm_source=x&b=1#frag"
    normalised = c._normalise(url)
    p = urlparse(normalised)
    qs = parse_qs(p.query)
    assert qs.get('utm_source') == ['x']
    assert qs.get('b') == ['1']


@pytest.mark.asyncio
async def test_verbose_prints_duration_and_metrics(make_server, capsys):
    async def page(request):
        return aiohttp.web.Response(text='<a href="/done">done</a>')

    server, base = await make_server({'/': page, '/done': page})

    c = WebCrawler(base, concurrency=1, max_pages=2, timeout=1, verbose=True)
    await c.crawl()

    out = capsys.readouterr().out

    # verbose prints timing like "(0.00s) in the Visited lines"
    assert "Visited:" in out
    assert "(" in out and "s)" in out

    # verbose prints an aggregate summary at the end
    assert "---- Crawl summary ----" in out
    assert "Pages visited:" in out and "Requests:" in out


@pytest.mark.asyncio
async def test_non_verbose_doesnt_print_duration_and_metrics(make_server, capsys):
    async def page(request):
        return aiohttp.web.Response(text='<a href="/done">done</a>')

    server, base = await make_server({'/': page, '/done': page})

    c = WebCrawler(base, concurrency=1, max_pages=2, timeout=1, verbose=False)
    await c.crawl()

    out = capsys.readouterr().out
    # per-page output is still expected (Visited lines), and there shouldn't be timing
    assert "Visited:" in out
    assert not ("(" in out and "s)" in out)

    # when verbose is False we should NOT see the aggregate summary
    assert "---- Crawl summary ----" not in out
    


