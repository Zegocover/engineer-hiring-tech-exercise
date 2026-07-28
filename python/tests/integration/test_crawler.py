import pytest

from tests.integration.helpers.crawler import run_crawler


class TestCrawler:
    @pytest.mark.parametrize("site", ["cycle", "self_link"], indirect=True)
    def test_terminates(self, site):
        "Crawling a cyclic or self-referential site must still terminate."
        url, transport, _requests = site
        result = run_crawler(url, timeout=5, transport=transport)
        assert result.completed

    @pytest.mark.parametrize("site", ["self_link"], indirect=True)
    def test_crawling_a_page_linking_only_itself(self, site):
        "A page that only links to itself should not cause infinite recursion."
        # Arrange
        url, transport, requests = site

        # Act
        result = run_crawler(url, timeout=5, transport=transport)

        # Assert
        assert result.completed
        assert result.visited == {url}
        assert result.urls == result.visited
        get_requests = [(method, path) for method, path, _ts in requests if method == "GET"]
        assert get_requests == [("GET", "/")]

    @pytest.mark.parametrize("site", ["cycle"], indirect=True)
    def test_two_pages_linking_to_each_other(self, site):
        "Two pages linking to each other should both be crawled exactly once."
        # Arrange
        url, transport, requests = site

        # Act
        result = run_crawler(url, timeout=5, transport=transport)

        # Assert
        assert result.completed
        assert result.visited == {url, f"{url}b"}
        assert result.urls == result.visited
        get_paths = [path for method, path, _ts in requests if method == "GET"]
        assert sorted(get_paths) == ["/", "/b"]
        assert len(get_paths) == len(set(get_paths))

    @pytest.mark.parametrize("site", ["commented_link"], indirect=True)
    def test_page_with_a_link_within_html_comment(self, site):
        "Links inside HTML comments should not be followed."
        # Arrange
        url, transport, requests = site

        # Act
        result = run_crawler(url, timeout=5, transport=transport)

        # Assert
        assert result.completed
        assert result.visited == {url, f"{url}real"}
        assert result.urls == result.visited
        get_paths = {path for method, path, _ts in requests if method == "GET"}
        assert "/ghost" not in get_paths

    @pytest.mark.parametrize("site", ["hundred_links"], indirect=True)
    def test_a_page_with_a_hundred_links_to_the_same_target(self, site):
        "Duplicate links to the same target should only be crawled once."
        # Arrange
        url, transport, requests = site

        # Act
        result = run_crawler(url, timeout=5, transport=transport)

        # Assert
        assert result.completed
        assert result.visited == {url, f"{url}target"}
        assert result.urls == result.visited
        get_paths = [path for method, path, _ts in requests if method == "GET" and path == "/target"]
        assert len(get_paths) == 1

    @pytest.mark.parametrize("site", ["nested_relative"], indirect=True)
    def test_a_relative_link_from_a_nested_path(self, site):
        "Relative links should resolve against their page's own path."
        # Arrange
        url, transport, _requests = site
        start_url = f"{url}deep/nested/page"

        # Act
        result = run_crawler(start_url, timeout=5, transport=transport)

        # Assert
        assert result.completed
        assert result.visited == {start_url, f"{url}deep/sibling"}
        assert result.urls == result.visited
