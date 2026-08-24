"""Pure URL algebra over :mod:`urllib.parse` and ``httpx.URL``.

No network. ``dedup_key`` canonicalises identity via ``httpx.URL``; other helpers do not.
"""

from __future__ import annotations

from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

import httpx

_HTTP_SCHEMES = frozenset({"http", "https"})


class InvalidBaseURLError(ValueError):
    """The base URL is not an absolute http(s) URL."""


def absolutize(base: str, href: str) -> str:
    """Resolve ``href`` against ``base`` into an absolute, fragment-stripped URL."""
    return urldefrag(urljoin(base, href)).url


def host(url: str) -> str:
    """Lower-cased hostname, or ``""`` if the URL has no host (e.g. ``mailto:``)."""
    return (urlsplit(url).hostname or "").lower()


def is_http(url: str) -> bool:
    """True for ``http``/``https`` URLs."""
    return urlsplit(url).scheme in _HTTP_SCHEMES


def same_host(url: str, base_host: str) -> bool:
    """Exact host match (case-insensitive; scheme/port ignored, subdomains distinct)."""
    return host(url) == base_host.lower()


def is_absolute_http(url: str) -> bool:
    """True for an absolute ``http``/``https`` URL with a host."""
    try:
        parsed = httpx.URL(url)
    except httpx.InvalidURL:
        return False
    return parsed.scheme in _HTTP_SCHEMES and bool(parsed.host)


def dedup_key(url: str) -> str:
    """Canonical crawl identity: lower-cased scheme/host, fragment dropped, empty path is ``/``."""
    parsed = httpx.URL(url)
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.raw_path.split(b"?", 1)[0].decode("ascii")
    query = parsed.query.decode("ascii")
    return f"{parsed.scheme}://{parsed.host}{port}{path}" + (f"?{query}" if query else "")


def robots_url(base_url: str) -> str:
    """The ``/robots.txt`` URL for ``base_url``'s scheme and authority."""
    parts = urlsplit(base_url)
    return urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
