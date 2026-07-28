from datetime import UTC, datetime, timedelta

import httpx
import pytest

from crawler.robots_cache import RobotsCache
from tests.integration.helpers.website import Page, make_app


def _cache_for(pages: dict[str, Page]) -> RobotsCache:
    app, _requests = make_app(pages)
    cache = RobotsCache()
    cache.client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testsite.local"
    )
    return cache


class TestRobotsCache:
    async def test_returns_cached_content_when_not_expired(self):
        "A domain with a live cache entry should return the cached content without hitting the network."
        # Arrange
        cache = _cache_for({})
        cache._cache["http://testsite.local"] = (
            datetime.now(UTC) + timedelta(minutes=5),
            "User-agent: *\nDisallow: /cached",
        )

        # Act
        result = await cache.fetch_robots_txt("http://testsite.local/page")

        # Assert
        assert result == "User-agent: *\nDisallow: /cached"

    async def test_refetches_when_cache_entry_expired(self):
        "An expired cache entry should be ignored and the robots.txt refetched."
        # Arrange
        cache = _cache_for(
            {"/robots.txt": Page("User-agent: *\nDisallow: /fresh", content_type="text/plain")}
        )
        cache._cache["http://testsite.local"] = (
            datetime.now(UTC) - timedelta(minutes=5),
            "stale",
        )

        # Act
        result = await cache.fetch_robots_txt("http://testsite.local/page")

        # Assert
        assert result == "User-agent: *\nDisallow: /fresh"

    async def test_returns_page_rules_on_200_with_text_plain(self):
        "A 200 response with a text/plain content type should return the body as-is."
        # Arrange
        cache = _cache_for(
            {"/robots.txt": Page("User-agent: *\nDisallow: /admin", content_type="text/plain")}
        )

        # Act
        result = await cache.fetch_robots_txt("http://testsite.local/")

        # Assert
        assert result == "User-agent: *\nDisallow: /admin"

    async def test_treats_200_html_content_type_as_404(self):
        "A 200 response whose Content-Type is not text/plain must be treated as a 404 (empty rules)."
        # Arrange
        cache = _cache_for(
            {"/robots.txt": Page("<html>not robots</html>", content_type="text/html")}
        )

        # Act
        result = await cache.fetch_robots_txt("http://testsite.local/")

        # Assert
        assert result == ""

    async def test_returns_empty_rules_on_404(self):
        "A genuine 404 for robots.txt means no rules apply, so an empty string is returned."
        # Arrange
        cache = _cache_for({})

        # Act
        result = await cache.fetch_robots_txt("http://testsite.local/")

        # Assert
        assert result == ""

    @pytest.mark.parametrize("status", [500, 503, 599])
    async def test_returns_none_on_5xx(self, status):
        "Any 5xx server error should block the crawl for that domain by returning None."
        # Arrange
        cache = _cache_for({"/robots.txt": Page(status=status)})

        # Act
        result = await cache.fetch_robots_txt("http://testsite.local/")

        # Assert
        assert result is None

    @pytest.mark.parametrize("status", [401, 403])
    async def test_returns_none_on_401_or_403(self, status):
        "401/403 on robots.txt should block the crawl for that domain by returning None."
        # Arrange
        cache = _cache_for({"/robots.txt": Page(status=status)})

        # Act
        result = await cache.fetch_robots_txt("http://testsite.local/")

        # Assert
        assert result is None

    @pytest.mark.parametrize("status", [301, 418, 429])
    async def test_returns_none_on_unexpected_status(self, status):
        "Any other unhandled status code should fall through to the catch-all branch and return None."
        # Arrange
        cache = _cache_for({"/robots.txt": Page(status=status)})

        # Act
        result = await cache.fetch_robots_txt("http://testsite.local/")

        # Assert
        assert result is None

    async def test_returns_none_on_too_many_redirects(self):
        "Exceeding max_redirects while fetching robots.txt should be caught and return None."
        # Arrange
        pages = {
            "/robots.txt": Page(status=302, headers={"Location": "/robots.txt"}),
        }
        app, _requests = make_app(pages)
        cache = RobotsCache(max_redirects=2)
        cache.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testsite.local",
            follow_redirects=True,
            max_redirects=2,
        )

        # Act
        result = await cache.fetch_robots_txt("http://testsite.local/")

        # Assert
        assert result is None

    async def test_returns_none_on_request_error(self):
        "A network-level error while fetching robots.txt should be caught and return None."

        # Arrange
        def _raise(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom", request=request)

        cache = RobotsCache()
        cache.client = httpx.AsyncClient(
            transport=httpx.MockTransport(_raise), base_url="http://testsite.local"
        )

        # Act
        result = await cache.fetch_robots_txt("http://testsite.local/")

        # Assert
        assert result is None
