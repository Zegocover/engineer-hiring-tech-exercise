import asyncio
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

from site_crawler.url_policy import UrlPolicy

USER_AGENT = "site-crawler/0.1 (+https://github.com/)"
REQUEST_TIMEOUT = 5.0
MAX_RETRIES = 3
MAX_REDIRECTS = 5


class NonHtmlContentError(httpx.HTTPError):
    """Raised when a fetched response is not an HTML document."""


class ExternalRedirectError(httpx.HTTPError):
    """Raised when a page redirects outside the crawl host."""


def _extract_response_links(
    response: httpx.Response, url: str, include_duplicates: bool
) -> list[str]:
    """
    Extract links from an HTTP response, verifying that it is HTML based on
    the content type header.
    """
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
    """
    Determine the delay before retrying a request after a 429 response. Uses
    the Retry-After header if present, otherwise uses exponential backoff.
    """
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
    """
    Extract absolute HTTP(S) links from an HTML document. Defaults to
    unique values; duplicates can be returned with include_duplicates=True.
    Fragments are removed from the URLs, and URLs without a path are normalized
    to have a trailing slash.
    """
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")
        if isinstance(href, str):
            absolute_url = urljoin(page_url, href)
            without_fragment, _ = urldefrag(absolute_url)
            parsed_url = urlsplit(without_fragment)
            if parsed_url.scheme.lower() in {"http", "https"}:
                parsed_url = parsed_url._replace(
                    scheme=parsed_url.scheme.lower()
                )
                if not parsed_url.path:
                    parsed_url = parsed_url._replace(path="/")
                links.append(urlunsplit(parsed_url))

    if include_duplicates:
        return tuple(links)
    return tuple(dict.fromkeys(links))


async def extract_links_from_url_async(
    client: httpx.AsyncClient,
    url: str,
    include_duplicates: bool = False,
    url_policy: UrlPolicy | None = None,
) -> list[str]:
    """
    Fetch and parse a page using a shared asynchronous HTTP client.
    Verifies that the page is HTML and that any redirects stay within
    the original domain. The number of redirects is limited to prevent
    infinite loops. If the page is rate-limited, it will be retried with
    exponential backoff, or after the Retry-After value from the header,
    if present.
    """
    current_url = url
    redirect_count = 0
    retry_attempt = 0

    while True:
        try:
            response = await client.get(
                current_url,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )

            # Keep redirects within the original domain.
            if 300 <= response.status_code < 400:
                location = response.headers.get("location")
                if location is None:
                    raise httpx.HTTPError(
                        "redirect response missing Location header"
                    )
                redirect_url = urljoin(current_url, location)
                if url_policy is not None and url_policy.normalize(
                    redirect_url
                ) is None:
                    raise ExternalRedirectError(
                        f"redirect outside original host: {redirect_url}"
                    )
                redirect_count += 1
                if redirect_count > MAX_REDIRECTS:
                    raise httpx.TooManyRedirects(
                        "maximum redirect count exceeded",
                        request=response.request,
                    )
                current_url = redirect_url
                retry_attempt = 0
                continue
            return _extract_response_links(
                response, current_url, include_duplicates
            )
        except httpx.HTTPStatusError as error:
            if (
                error.response.status_code == 429
                and retry_attempt < MAX_RETRIES - 1
            ):
                await asyncio.sleep(
                    _retry_delay(error.response, retry_attempt)
                )
                retry_attempt += 1
                continue
            raise
