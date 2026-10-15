"""URL resolution, normalisation and scope checks.

Normalisation is deliberately conservative: only transformations that cannot
change which resource a server returns are applied. Trailing slashes and
query parameter order are left alone.
"""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit

from site_crawler.models.hosts import HostPattern

_DEFAULT_PORTS = {"http": 80, "https": 443}
_HTTP_SCHEMES = frozenset(_DEFAULT_PORTS)


def resolve(base: str, href: str) -> str | None:
    """Resolve ``href`` against ``base``; return ``None`` for unusable hrefs."""
    href = href.strip()
    if not href:
        return None
    try:
        return urljoin(base, href)
    except ValueError:  # e.g. malformed IPv6 netloc
        return None


def normalise(url: str) -> str | None:
    """Return a canonical form of an absolute http(s) URL, or ``None``.

    Lowercases scheme and host, drops default ports and the fragment, and
    turns an empty path into ``/``.
    """
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    host = parts.hostname
    if scheme not in _HTTP_SCHEMES or not host:
        return None
    netloc = host if ":" not in host else f"[{host}]"
    if port is not None and port != _DEFAULT_PORTS[scheme]:
        netloc = f"{netloc}:{port}"
    if parts.username or parts.password:
        userinfo = parts.username or ""
        if parts.password:
            userinfo += f":{parts.password}"
        netloc = f"{userinfo}@{netloc}"
    return urlunsplit((scheme, netloc, parts.path or "/", parts.query, ""))


def resolve_and_normalise(base: str, href: str) -> str | None:
    resolved = resolve(base, href)
    return normalise(resolved) if resolved is not None else None


def host_key(url: str) -> str | None:
    """Host identity used for scope checks: hostname plus non-default port.

    Scheme is ignored, so http and https on the same host are one site.
    """
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in _HTTP_SCHEMES or not parts.hostname:
        return None
    if port is None or port == _DEFAULT_PORTS[scheme]:
        return parts.hostname
    return f"{parts.hostname}:{port}"


def same_host(url: str, host: str) -> bool:
    return host_key(url) == host


def host_and_port(url: str) -> tuple[str, int | None] | None:
    """Lowercase hostname and non-default port of an http(s) URL, or ``None``."""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in _HTTP_SCHEMES or not parts.hostname:
        return None
    return parts.hostname.rstrip("."), None if port in (None, _DEFAULT_PORTS[scheme]) else port


class HostScope:
    """The hosts a crawl may fetch from: its base host plus any allowed patterns.

    Matching ignores case, default ports and the scheme, like :func:`same_host`.
    """

    def __init__(self, base_url: str, patterns: Iterable[HostPattern] = ()) -> None:
        base = host_and_port(base_url)
        if base is None:
            raise ValueError(f"unusable base URL {base_url!r}")
        self._base = base
        self._patterns = tuple(patterns)

    def allows(self, url: str) -> bool:
        target = host_and_port(url)
        if target is None:
            return False
        if target == self._base:
            return True
        return any(p.matches(*target) for p in self._patterns)
