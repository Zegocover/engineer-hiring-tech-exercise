from pathlib import Path

import pytest

from crawlspace._fetcher import Fetcher
from crawlspace.schemas import FetchResult


async def test_fetcher(website, html):
    fetcher = Fetcher()

    page = html.get(Path("index.html"))

    url: str = website
    result: FetchResult = await fetcher.fetch(url)

    assert result == FetchResult(url=url, status=200, text=page)


@pytest.mark.parametrize(
    "page_path, error",
    [
        ("missing_page.html", 404),
        ("broken_page.html", 500),
    ],
)
async def test_fetcher_returns_status_and_error_page_for_bad_status(
    website, html, page_path, error
):
    fetcher = Fetcher()

    page = html.get(Path(f"{error}.html"))

    url: str = f"{website}/{page_path}"
    result: FetchResult = await fetcher.fetch(url)

    assert result == FetchResult(url=url, status=error, text=page)


async def test_fetcher_returns_minus_1_and_empty_page_on_connection_error():
    fetcher = Fetcher()

    url: str = f"http://localhost:8889"
    result: FetchResult = await fetcher.fetch(url)

    assert result == FetchResult(url=url, status=-1, text="")
