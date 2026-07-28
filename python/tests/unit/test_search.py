import asyncio

import pytest

from crawler.search import BredthFirstSearch, UrlNormaliser

normalise = UrlNormaliser().normalise

HOST = "https://a.test"


def link_map(pages: dict[str, list[str]]):
    """Builds a `get_links` backed by a dict, recording call order."""
    calls: list[str] = []

    async def get_links(url: str) -> list[str]:
        calls.append(url)
        return pages.get(url, [])

    return get_links, calls


class TestUrlNormaliser:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://a.test/page/", "https://a.test/page"),
            ("https://a.test/page", "https://a.test/page"),
            ("https://a.test/deep/page///", "https://a.test/deep/page"),
        ],
    )
    def test_drops_trailing_slashes(self, url, expected):
        "A trailing slash does not select a different resource."
        assert normalise(url) == expected

    @pytest.mark.parametrize("url", ["https://a.test/", "https://a.test"])
    def test_root_path_survives_as_a_single_slash(self, url):
        "Stripping the slash from a root URL must not leave an empty path."
        assert normalise(url) == "https://a.test/"

    def test_strips_tracking_params(self):
        "utm_* and friends tell the target where a visitor came from, not which page."
        assert (
            normalise("https://a.test/p?utm_source=x&utm_medium=y&gclid=z")
            == "https://a.test/p"
        )

    def test_keeps_meaningful_query_params(self):
        "A query that selects content must survive, and tracking around it is dropped."
        assert (
            normalise("https://a.test/search?q=spiders&utm_source=x")
            == "https://a.test/search?q=spiders"
        )

    def test_lowercases_scheme_and_host_but_not_path(self):
        "Scheme and host are case-insensitive; the path may be significant to the server."
        assert normalise("HTTPS://A.TEST/CasePath") == "https://a.test/CasePath"

    def test_discards_fragments(self):
        "A fragment addresses a position within a page, not a separate page."
        assert normalise("https://a.test/p#section") == "https://a.test/p"

    def test_collapses_the_variants_to_one_value(self):
        "The whole point: these spellings are one resource."
        variants = {
            "https://a.test/page",
            "https://a.test/page/",
            "https://a.test/page?utm_source=newsletter",
            "https://A.test/page#top",
        }
        assert len({normalise(url) for url in variants}) == 1


class TestBredthFirstSearch:
    async def test_visits_every_reachable_page_once(self):
        "A linear chain should be fully traversed, each page fetched exactly once."
        # Arrange
        get_links, calls = link_map(
            {
                f"{HOST}/": [f"{HOST}/a"],
                f"{HOST}/a": [f"{HOST}/b"],
                f"{HOST}/b": [],
            }
        )

        # Act
        visited, _found = await BredthFirstSearch(f"{HOST}/", get_links).run()

        # Assert
        assert visited == {f"{HOST}/", f"{HOST}/a", f"{HOST}/b"}
        assert sorted(calls) == [f"{HOST}/", f"{HOST}/a", f"{HOST}/b"]

    async def test_a_cycle_terminates(self):
        "Two pages linking to each other must not loop forever."
        # Arrange
        get_links, calls = link_map(
            {f"{HOST}/": [f"{HOST}/b"], f"{HOST}/b": [f"{HOST}/"]}
        )

        # Act
        visited, _found = await BredthFirstSearch(f"{HOST}/", get_links).run()

        # Assert
        assert visited == {f"{HOST}/", f"{HOST}/b"}
        assert len(calls) == 2

    async def test_repeated_links_to_one_target_fetch_it_once(self):
        "Many links to the same page should collapse to a single fetch."
        # Arrange
        get_links, calls = link_map(
            {f"{HOST}/": [f"{HOST}/target"] * 50, f"{HOST}/target": []}
        )

        # Act
        await BredthFirstSearch(f"{HOST}/", get_links).run()

        # Assert
        assert calls.count(f"{HOST}/target") == 1

    async def test_url_variants_of_one_page_are_visited_once(self):
        "Traversal keys on the normalised URL, so spellings collapse."
        # Arrange
        get_links, calls = link_map(
            {
                f"{HOST}/": [
                    f"{HOST}/page",
                    f"{HOST}/page/",
                    f"{HOST}/page?utm_source=x",
                    f"{HOST}/page#top",
                ],
                f"{HOST}/page": [],
            }
        )

        # Act
        visited, _found = await BredthFirstSearch(f"{HOST}/", get_links).run()

        # Assert
        assert visited == {f"{HOST}/", f"{HOST}/page"}
        assert calls.count(f"{HOST}/page") == 1

    async def test_off_domain_links_are_recorded_but_not_traversed(self):
        "Other domains belong in found_urls_by_domain, never in the queue."
        # Arrange
        get_links, calls = link_map(
            {f"{HOST}/": ["https://other.test/x", f"{HOST}/local"], f"{HOST}/local": []}
        )

        # Act
        visited, found = await BredthFirstSearch(f"{HOST}/", get_links).run()

        # Assert
        assert visited == {f"{HOST}/", f"{HOST}/local"}
        assert "https://other.test/x" not in calls
        assert found["other.test"] == {"https://other.test/x"}

    async def test_found_urls_keep_the_spelling_the_page_used(self):
        "Reporting records the raw link; only traversal uses the normalised form."
        # Arrange
        get_links, _calls = link_map(
            {f"{HOST}/": [f"{HOST}/page/?utm_source=x"], f"{HOST}/page": []}
        )

        # Act
        visited, found = await BredthFirstSearch(f"{HOST}/", get_links).run()

        # Assert
        assert found["a.test"] == {f"{HOST}/page/?utm_source=x"}
        assert visited == {f"{HOST}/", f"{HOST}/page"}

    async def test_the_start_url_is_normalised(self):
        "A start URL with a trailing slash or fragment is canonicalised up front."
        # Act
        bfs = BredthFirstSearch(f"{HOST}/start/#top", link_map({})[0])

        # Assert
        assert bfs.start_url == f"{HOST}/start"
        assert bfs.visited == {f"{HOST}/start"}

    async def test_never_exceeds_max_concurrency(self):
        "In-flight fetches must be capped by the worker count, not the link count."
        # Arrange
        in_flight = 0
        peak = 0

        async def get_links(url: str) -> list[str]:
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            # Yield so the other workers get a chance to pile on.
            await asyncio.sleep(0)
            in_flight -= 1
            return [f"{HOST}/p{i}" for i in range(20)] if url == f"{HOST}/" else []

        # Act
        await BredthFirstSearch(f"{HOST}/", get_links, max_concurrency=3).run()

        # Assert
        assert peak <= 3

    async def test_an_empty_site_returns_just_the_start_url(self):
        "A page with no links is a complete crawl of one page."
        # Act
        visited, found = await BredthFirstSearch(f"{HOST}/", link_map({})[0]).run()

        # Assert
        assert visited == {f"{HOST}/"}
        assert found == {}
