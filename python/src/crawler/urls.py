"""URL normalisation and filtering helpers."""

import urllib.parse as parse

SUPPORTED_SCHEMES = {"http", "https"}


class UrlParsingError(ValueError):
    """Raised when a URL cannot be parsed safely."""


def normalise_for_dedupe(url: str) -> str:
    """Normalise an absolute URL for dedupe.

    Call after resolving links so a scheme is present.
    """
    parsed = parse.urlparse(url)
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port

    netloc = host
    if port and not (
        (scheme == "http" and port == 80)
        or (scheme == "https" and port == 443)
    ):
        netloc = f"{host}:{port}"

    path = parsed.path
    if path.endswith("/"):
        path = path.rstrip("/")

    return parse.urlunparse(
        (
            scheme,
            netloc,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


def resolve_url(referrer: str, href: str) -> str:
    """Resolve a possibly relative link against a referrer URL."""
    return parse.urljoin(referrer, href)


def strip_fragment(url: str) -> str:
    """Return the URL without any fragment."""
    parsed = parse.urlparse(url)
    if not parsed.fragment:
        return url
    return parse.urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            "",
        )
    )


def is_supported_scheme(url: str) -> bool:
    """Return True if the URL scheme is supported.

    Call after resolving links so a scheme is present.
    """
    scheme = parse.urlparse(url).scheme.lower()
    if not scheme:
        raise UrlParsingError(f"URL has no scheme: {url}")
    return scheme in SUPPORTED_SCHEMES


def is_domain_in_scope(url: str, base_url: str) -> bool:
    """Return True if the URL hostname matches the base URL hostname."""
    url_host = parse.urlparse(url).hostname
    base_host = parse.urlparse(base_url).hostname
    if not url_host or not base_host:
        raise UrlParsingError(
            f"URL or base URL has no hostname: {url} | {base_url}"
        )
    return url_host.lower() == base_host.lower()


def validate_base_url(value: str) -> str:
    """Validate the base URL."""
    parsed = parse.urlparse(value)
    if parsed.scheme not in SUPPORTED_SCHEMES:
        raise UrlParsingError("Base URL must include http/https scheme")
    if not parsed.netloc:
        raise UrlParsingError("Base URL must include a domain")
    return value
