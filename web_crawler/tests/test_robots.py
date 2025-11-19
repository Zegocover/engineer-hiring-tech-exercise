import time
import pytest
import aiohttp
from web_crawler.src.robots import RobotsParser


@pytest.mark.asyncio
async def test_fetch_parses_rules_and_crawl_delay(make_server):
    async def robots(request):
        text = """
User-agent: *
Disallow: /blocked
Allow: /allowed
Crawl-delay: 0.5
"""
        return aiohttp.web.Response(text=text)

    server, base = await make_server({'/robots.txt': robots})

    async with aiohttp.ClientSession() as session:
        p = await RobotsParser.fetch(session, base)

    # crawl-delay parsed
    assert p.get_crawl_delay("*") == pytest.approx(0.5)
    # disallow/allow behavior
    assert not p.is_allowed(f"{base}/blocked", "*")
    assert p.is_allowed(f"{base}/allowed", "*")

@pytest.mark.asyncio
async def test_fetch_bad_request_means_empty_rules(make_server):
    async def robots_404(request):
        return aiohttp.web.Response(status=404, text='not found')

    server2, base2 = await make_server({'/robots.txt': robots_404})

    async with aiohttp.ClientSession() as session:
        p = await RobotsParser.fetch(session, base2)
         
    # no crawl delay and everything allowed by default
    assert p.get_crawl_delay("*") is None
    assert p.is_allowed(f"{base2}/allthesecrets", "*")


def test_is_allowed_user_agent_matching_and_priority():
    text = """
User-agent: mybot
Disallow: /nope

User-agent: *
Disallow: /allblocked
Allow: /allblocked/public
"""
    p = RobotsParser('https://example.com', text)

    # mybot should be blocked only by its rule
    assert not p.is_allowed('https://example.com/nope', 'mybot')
    assert p.is_allowed('https://example.com/allblocked', 'mybot')
    # other agents follow '*' rules
    assert not p.is_allowed('https://example.com/allblocked', 'Other')
    # allow takes precedence
    assert p.is_allowed('https://example.com/allblocked/public', 'Other')


def test_is_allowed_empty_disallow_allows_everything():
    text = """
User-agent: *
Disallow:
"""
    p = RobotsParser("http://example.com", text)
    assert p.is_allowed("http://example.com/allthesecrets", "*")


def test_is_allowed_disallow_root_allows_nothing():
    text = """
User-agent: *
Disallow: /
"""
    p = RobotsParser("http://example.com", text)
    assert not p.is_allowed("http://example.com/", "*")
    assert not p.is_allowed("http://example.com/allthesecrets", "*")


def test_get_crawl_delay_returns_crawl_delay():
    text = """
User-agent: *
Crawl-delay: 5
"""
    p = RobotsParser("http://example.com", text)
    assert p.get_crawl_delay("*") == 5


def test_get_crawl_delay_malformed_crawl_delay_ignored():
    text = """
User-agent: *
Crawl-delay: not-a-number
"""
    p = RobotsParser("http://example.com", text)
    assert p.get_crawl_delay("*") is None
    