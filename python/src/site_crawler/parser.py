import asyncio
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "site-crawler/0.1 (+https://github.com/)"
REQUEST_TIMEOUT = 5.0
MAX_RETRIES = 3


class NonHtmlContentError(httpx.HTTPError):
    """Raised when a fetched response is not an HTML document."""


def _extract_response_links(
    response: httpx.Response, url: str, include_duplicates: bool
) -> list[str]:
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if content_type and not any(
        html_type in content_type.lower()
        for html_type in ("text/html", "application/xhtml+xml")
    ):
        raise NonHtmlContentError(
            f"unsupported content type: {content_type}"
        )
    return list(extract_links(response.text, url, include_duplicates))


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("retry-after")
    if retry_after is not None:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass
    return float(2**attempt)


def extract_links(
    html: str, page_url: str, include_duplicates: bool = False
) -> tuple[str, ...]:
    """Extract absolute HTTP(S) links from an HTML document."""
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")
        if isinstance(href, str):
            absolute_url = urljoin(page_url, href)
            without_fragment, _ = urldefrag(absolute_url)
            if without_fragment.startswith(("http://", "https://")):
                parsed_url = urlsplit(without_fragment)
                if not parsed_url.path:
                    without_fragment = urlunsplit(
                        parsed_url._replace(path="/")
                    )
                links.append(without_fragment)

    if include_duplicates:
        return tuple(links)
    return tuple(dict.fromkeys(links))


async def extract_links_from_url_async(
    client: httpx.AsyncClient, url: str, include_duplicates: bool = False
) -> list[str]:
    """Fetch and parse a page using a shared asynchronous HTTP client."""
    for attempt in range(MAX_RETRIES):
        try:
            response = await client.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )
            return _extract_response_links(response, url, include_duplicates)
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 429 and attempt < MAX_RETRIES - 1:
                await asyncio.sleep(_retry_delay(error.response, attempt))
                continue
            raise
