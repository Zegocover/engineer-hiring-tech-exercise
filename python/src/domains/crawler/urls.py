"""Pure URL helpers for the crawler. Standard library only — no I/O."""

from urllib.parse import urljoin, urlsplit, urlunsplit

_DEFAULT_PORTS = {"http": "80", "https": "443"}
_FOLLOWABLE_SCHEMES = {"http", "https"}


def _normalize_netloc(scheme: str, netloc: str) -> str:
    """Lowercase the host and drop the port when it is the scheme default."""
    host, _, port = netloc.partition(":")
    host = host.lower()
    if port and port == _DEFAULT_PORTS.get(scheme):
        return host
    return f"{host}:{port}" if port else host


def normalize(href: str, base_url: str) -> str | None:
    """Resolve `href` against `base_url` into an absolute, canonical URL.

    Returns None for non-navigable links (mailto/tel/javascript/data, bare
    fragments, or anything that does not resolve to http/https).
    """
    stripped = href.strip()
    # Bare fragment-only hrefs (e.g. "#section") resolve to the base URL — treat as non-navigable.
    raw = urlsplit(stripped)
    if not raw.scheme and not raw.netloc and not raw.path and not raw.query:
        return None
    absolute = urljoin(base_url, stripped)
    parts = urlsplit(absolute)
    if parts.scheme not in _FOLLOWABLE_SCHEMES:
        return None
    netloc = _normalize_netloc(parts.scheme, parts.netloc)
    if not netloc:
        return None
    path = parts.path or "/"
    return urlunsplit((parts.scheme, netloc, path, parts.query, ""))


def extract_host(url: str) -> str:
    """Return the canonical host[:port] of `url` (lowercased, default port dropped)."""
    parts = urlsplit(url)
    return _normalize_netloc(parts.scheme, parts.netloc)


def same_host(url: str, host: str) -> bool:
    """True iff `url`'s canonical host equals `host` (exact match; subdomains differ)."""
    return extract_host(url) == host.lower()
