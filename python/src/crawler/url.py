"""URL helpers for normalization, scheme filtering and domain scoping."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

_DEFAULT_PORTS = {"http": 80, "https": 443}
_HTTP_SCHEMES = frozenset({"http", "https"})


def is_http_url(url: str) -> bool:
    """Return ``True`` for absolute ``http``/``https`` URLs.

    Filters out non-navigable schemes such as ``mailto:``, ``tel:``,
    ``javascript:`` and ``data:``. Relative URLs (no scheme) return ``False``;
    callers resolve links against the page URL *before* checking.
    """
    return urlsplit(url).scheme.lower() in _HTTP_SCHEMES


def get_host(url: str) -> str | None:
    """Return the lower-cased host of ``url`` with any leading ``www.`` removed,
    or ``None`` if the URL has no host.

    Stripping ``www.`` here means ``example.com`` and ``www.example.com`` share a
    single canonical host, which is how :func:`same_site` treats them as one site.
    """
    host = urlsplit(url).hostname
    if not host:
        return None
    return _strip_www(host)


def same_site(url: str, base_host: str, *, include_subdomains: bool = False) -> bool:
    """Return ``True`` if ``url`` belongs to the site identified by ``base_host``.

    ``base_host`` is expected to be a canonical host as produced by
    :func:`get_host`. ``www.`` is treated as equivalent to the apex domain. By
    default other subdomains (``blog.example.com``) are excluded; passing
    ``include_subdomains=True`` widens the scope to any subdomain of the base.
    """
    host = get_host(url)
    if host is None:
        return False
    base = _strip_www(base_host.lower())
    if include_subdomains:
        return host == base or host.endswith(f".{base}")
    return host == base


def normalize(url: str) -> str:
    """Return a canonical form of ``url`` for de-duplication.

    Applies only transformations that cannot merge two genuinely different
    resources: strip the fragment, lower-case scheme and host, drop the default
    port, canonicalize an empty path to ``/``, and resolve ``.``/``..`` segments.
    """
    parts = urlsplit(url)
    scheme = parts.scheme.lower()

    netloc = _canonical_netloc(scheme, parts.hostname, parts.port)

    path = _remove_dot_segments(parts.path)
    if not path and netloc:
        path = "/"

    return urlunsplit((scheme, netloc, path, parts.query, ""))


def _strip_www(host: str) -> str:
    host = host.lower().rstrip(".")
    prefix = "www."
    return host[len(prefix) :] if host.startswith(prefix) else host


def _canonical_netloc(scheme: str, hostname: str | None, port: int | None) -> str:
    if not hostname:
        return ""
    host = hostname.rstrip(".")
    if ":" in host:  # IPv6 literal — urlsplit strips the surrounding brackets
        host = f"[{host}]"
    if port is not None and _DEFAULT_PORTS.get(scheme) != port:
        return f"{host}:{port}"
    return host


def _remove_dot_segments(path: str) -> str:
    """Resolve ``.`` and ``..`` segments (RFC 3986 §5.2.4).

    Consecutive slashes are collapsed as a side effect, which for a crawler just
    means fewer duplicate fetches.
    """
    if not path:
        return ""
    segments = path.split("/")
    # A trailing "." or ".." denotes a directory, i.e. keeps a trailing slash.
    keep_trailing_slash = path.endswith("/") or segments[-1] in (".", "..")

    out: list[str] = []
    for segment in segments:
        if segment in ("", "."):
            continue
        if segment == "..":
            if out:
                out.pop()
        else:
            out.append(segment)

    resolved = "/".join(out)
    if not resolved and not path.startswith("/"):
        return ""
    if path.startswith("/"):
        resolved = "/" + resolved
    if keep_trailing_slash and not resolved.endswith("/"):
        resolved += "/"
    return resolved
