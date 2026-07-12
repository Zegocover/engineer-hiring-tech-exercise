import httpx
import pytest
import respx

from crawler.src.fetcher import Fetcher
from crawler.src.robots import ProtegoRobotsPolicy, load_robots_policy

ROBOTS_TXT_BASIC = """
User-agent: *
Disallow: /private
"""

ROBOTS_TXT_PER_AGENT = """
User-agent: specific-bot
Disallow: /only-for-specific

User-agent: *
Disallow: /for-everyone
"""

def test_allows_paths_not_disallowed():
    policy = ProtegoRobotsPolicy(ROBOTS_TXT_BASIC, "*")
    assert policy.is_allowed("https://example.com/public") is True


def test_disallows_matching_path():
    policy = ProtegoRobotsPolicy(ROBOTS_TXT_BASIC, "*")
    assert policy.is_allowed("https://example.com/private/secret") is False


def test_uses_specific_user_agent_group_over_wildcard():
    policy = ProtegoRobotsPolicy(ROBOTS_TXT_PER_AGENT, "specific-bot")
    assert policy.is_allowed("https://example.com/only-for-specific") is False
    # Per the rFC, any specific-bot group fully overrides the wildcard group for that specific-bot.
    # Also rules don't merge across different groups.
    assert policy.is_allowed("https://example.com/for-everyone") is True


def test_falls_back_to_wildcard_group_for_unlisted_agents():
    policy = ProtegoRobotsPolicy(ROBOTS_TXT_PER_AGENT, "other-bot")
    assert policy.is_allowed("https://example.com/only-for-specific") is True
    assert policy.is_allowed("https://example.com/for-everyone") is False


def test_crawl_delay_returns_parsed_value():
    policy = ProtegoRobotsPolicy("User-agent: *\nCrawl-delay: 5\n", "*")
    assert policy.crawl_delay == pytest.approx(5.0)


def test_crawl_delay_returns_none_when_unspecified():
    policy = ProtegoRobotsPolicy(ROBOTS_TXT_BASIC, "*")
    assert policy.crawl_delay is None


def test_empty_robots_txt_allows_everything():
    policy = ProtegoRobotsPolicy("", "*")
    assert policy.is_allowed("https://example.com/anything") is True
    assert policy.crawl_delay is None


@pytest.mark.asyncio
async def test_load_robots_policy_parses_fetched_content():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/robots.txt").mock(return_value=httpx.Response(200, text=ROBOTS_TXT_BASIC))
            fetcher = Fetcher(client, max_retries=0)
            policy = await load_robots_policy("https://example.com/some/page", fetcher, "*")

    assert policy.is_allowed("https://example.com/public") is True
    assert policy.is_allowed("https://example.com/private/secret") is False


@pytest.mark.asyncio
async def test_load_robots_policy_requests_robots_txt_at_domain_root():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/robots.txt").mock(return_value=httpx.Response(200, text=""))
            fetcher = Fetcher(client, max_retries=0)
            # robots.txt must be requested at the domain root, not relative to teh current path.
            await load_robots_policy("https://example.com/deeply/nested/page?x=1", fetcher, "*")

    assert route.called
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_load_robots_policy_fails_open_on_missing_robots_txt():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/robots.txt").mock(return_value=httpx.Response(404))
            fetcher = Fetcher(client, max_retries=0)
            policy = await load_robots_policy("https://example.com", fetcher, "*")

    assert policy.is_allowed("https://example.com/anything") is True
    assert policy.crawl_delay is None


@pytest.mark.asyncio
async def test_load_robots_policy_fails_open_when_retries_exhausted():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/robots.txt").mock(return_value=httpx.Response(503))
            fetcher = Fetcher(client, max_retries=1, backoff_base=0.01, backoff_cap=0.02)
            policy = await load_robots_policy("https://example.com", fetcher, "*")

    assert policy.is_allowed("https://example.com/anything") is True


@pytest.mark.asyncio
async def test_load_robots_policy_fails_open_on_connection_error():
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/robots.txt").mock(side_effect=httpx.ConnectError("boom"))
            fetcher = Fetcher(client, max_retries=0, backoff_base=0.01, backoff_cap=0.02)
            policy = await load_robots_policy("https://example.com", fetcher, "*")

    assert policy.is_allowed("https://example.com/anything") is True


@pytest.mark.asyncio
async def test_load_robots_policy_ignores_content_type():
    # Real servers often mislabel robots.txt (or omit the content-type) we will
    # still parse ir rather than reject it
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/robots.txt").mock(
                return_value=httpx.Response(
                    200, headers={"content-type": "text/html"}, text=ROBOTS_TXT_BASIC
                )
            )
            fetcher = Fetcher(client, max_retries=0)
            policy = await load_robots_policy("https://example.com", fetcher, "*")

    assert policy.is_allowed("https://example.com/private/x") is False
