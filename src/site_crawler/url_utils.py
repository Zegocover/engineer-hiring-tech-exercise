"""URL normalisation and same-host filtering."""

from urllib.parse import urldefrag, urljoin, urlparse, urlunparse


def canonical_url(url, base_url=None):
    """Resolve a link against a base URL and drop the fragment.

    ``https://Example.com:443/a#x`` and ``https://example.com/a`` become
    the same crawl key. The path and query are left unchanged, because
    ``/a`` and ``/a/`` can be different resources.
    """
    absolute = urljoin(base_url, url.strip()) if base_url else url.strip()
    without_fragment, _fragment = urldefrag(absolute)
    parts = urlparse(without_fragment)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None

    hostname = parts.hostname.lower()
    port = parts.port
    if port and not _is_default_port(parts.scheme, port):
        netloc = "%s:%s" % (hostname, port)
    else:
        netloc = hostname

    path = parts.path or "/"
    return urlunparse((parts.scheme.lower(), netloc, path, "", parts.query, ""))


def hostname_of(url):
    parsed = urlparse(url)
    return parsed.hostname.lower() if parsed.hostname else ""


def same_site(url, root_host):
    """True only for the exact host. Subdomains are a different site."""
    return hostname_of(url) == root_host


def _is_default_port(scheme, port):
    return (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
