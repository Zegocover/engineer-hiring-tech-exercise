from __future__ import annotations

from typing import Protocol
from urllib.parse import (
    SplitResult,
    parse_qsl,
    urldefrag,
    urlencode,
    urljoin,
    urlsplit,
    urlunsplit,
)

_DEFAULT_PORTS = {"http": 80, "https": 443}


class URLNormaliser(Protocol):
    """"""
    def normalise_url(self, href: str, base_url: str) -> str | None: ...


class DefaultURLNormaliser:
    @staticmethod
    def _extract_url_parts(href: str, base_url: str) -> SplitResult:
        absolute, _ = urldefrag(urljoin(base_url, href))
        return urlsplit(absolute)

    @staticmethod
    def _extract_host(hostname: str, parts: SplitResult) -> str:
        normalised_hostname =  hostname.lower()
        if parts.port and parts.port != _DEFAULT_PORTS[parts.scheme]:
            return f"{normalised_hostname}:{parts.port}"

        return normalised_hostname

    def normalise_url(self, href: str, base_url: str) -> str | None:
        href = href.strip()
        if not href:
            return None

        parts = self._extract_url_parts(href, base_url)

        if parts.scheme not in ("http", "https"):
            return None  # ignores mailto:, javascript:, tel:, and anything else non-http(s)

        hostname = parts.hostname
        if not hostname:
            return None

        network_location = self._extract_host(hostname, parts)

        path = parts.path or "/"
        query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))

        return urlunsplit((parts.scheme, network_location, path, query, ""))
